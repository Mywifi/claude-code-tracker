import os
import logging
import httpx
import uvicorn
import json
import threading
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .utils import check_dns_private
# from .reporter import generate_report  # No longer used

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("claude_tracker")

# Configuration
TARGET_SERVER = os.environ.get("TARGET_SERVER", "http://localhost:8080").rstrip("/")
VERIFY_SSL = os.environ.get("VERIFY_SSL", "true").lower() == "true"
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS_FILE = DATA_DIR / os.environ.get("PROMPTS_FILE", "ai_prompts.json")
PROMPTS_FILE_LOCK = threading.Lock()

app = FastAPI(title="Claude Tracker Proxy")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/report/static", StaticFiles(directory=str(static_dir)), name="static")

# Shared AsyncClient for connection pooling
http_client = httpx.AsyncClient(timeout=600.0, verify=VERIFY_SSL, trust_env=True)

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

def save_interaction(request_body: dict, response_data: any = None, timestamp: str = None):
    """Save interaction to JSON file."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    
    try:
        interaction_data = {
            "timestamp": timestamp,
            "model": request_body.get("model", ""),
            "full_request": request_body,
            "full_response": response_data
        }
        
        with PROMPTS_FILE_LOCK:
            if PROMPTS_FILE.exists():
                try:
                    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    data = {"extraction_time": datetime.now().isoformat(), "prompts": []}
            else:
                data = {"extraction_time": datetime.now().isoformat(), "prompts": []}
            
            data["prompts"].append(interaction_data)
            data["total_prompts"] = len(data["prompts"])
            data["last_updated"] = datetime.now().isoformat()
            
            with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save interaction: {e}")

@app.post("/v1/messages")
async def forward_messages(request: Request):
    path_with_query = request.url.path
    if request.url.query:
        path_with_query += f"?{request.url.query}"
    url = f"{TARGET_SERVER}{path_with_query}"
    
    method = request.method
    body = await request.body()
    
    is_stream = False
    body_json = None
    request_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    try:
        body_json = json.loads(body)
        is_stream = body_json.get("stream", False)
    except json.JSONDecodeError:
        pass

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # MiniMax compatibility
    if "minimax" in TARGET_SERVER.lower() and "authorization" in headers:
        auth = headers.get("authorization", "")
        if auth.startswith("Bearer "):
            headers["x-api-key"] = auth[7:].strip()

    logger.info(f"Forwarding {method} {url} (stream={is_stream})")

    # SSL & Private IP Check
    actual_verify_ssl = VERIFY_SSL
    dns_private, ip = check_dns_private(httpx.URL(url).host)
    if dns_private:
        logger.warning(f"Private IP detected ({ip}). Disabling SSL verify.")
        actual_verify_ssl = False

    if is_stream:
        async def stream_generator():
            full_response_chunks = []
            try:
                client = http_client if actual_verify_ssl == VERIFY_SSL else \
                         httpx.AsyncClient(timeout=600.0, verify=False, trust_env=True)
                
                async with client.stream(method, url, content=body, headers=headers, follow_redirects=True) as response:
                    async for chunk in response.aiter_bytes():
                        full_response_chunks.append(chunk)
                        yield chunk
                
                if client != http_client:
                    await client.aclose()
                
                try:
                    full_res_text = b"".join(full_response_chunks).decode("utf-8", errors="replace")
                    save_interaction(body_json, {"raw_stream": full_res_text}, request_timestamp)
                except Exception as e:
                    logger.warning(f"Failed to save streamed interaction: {e}")
                    
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield json.dumps({"error": str(e)}).encode()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        try:
            client = http_client if actual_verify_ssl == VERIFY_SSL else \
                     httpx.AsyncClient(timeout=600.0, verify=False, trust_env=True)
            
            response = await client.request(method, url, content=body, headers=headers, follow_redirects=True)
            
            res_headers = dict(response.headers)
            res_headers.pop("content-encoding", None)
            res_headers.pop("content-length", None)
            res_headers.pop("transfer-encoding", None)
            
            if client != http_client:
                await client.aclose()
            
            try:
                res_content = response.content.decode("utf-8", errors="replace")
                try:
                    res_json = json.loads(res_content)
                    save_interaction(body_json, res_json, request_timestamp)
                except json.JSONDecodeError:
                    save_interaction(body_json, res_content, request_timestamp)
            except Exception as e:
                logger.warning(f"Failed to save interaction: {e}")
            
            return StreamingResponse(iter([response.content]), status_code=response.status_code, headers=res_headers)
        except Exception as e:
            logger.error(f"Forwarding error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/messages/count_tokens")
async def forward_count_tokens(request: Request):
    # Similar to messages but simplified
    path = request.url.path
    url = f"{TARGET_SERVER}{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    try:
        response = await http_client.request(request.method, url, content=body, headers=headers)
        return StreamingResponse(iter([response.content]), status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Claude Tracker Proxy", "target": TARGET_SERVER, "report": "/report"}

@app.get("/report")
async def get_report():
    index_file = Path(__file__).parent / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_file))

@app.get("/report/data")
async def get_report_data():
    if not PROMPTS_FILE.exists():
        return {"extraction_time": datetime.now().isoformat(), "prompts": [], "total_prompts": 0, "last_updated": datetime.now().isoformat()}
    with PROMPTS_FILE_LOCK:
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

@app.get("/report/status")
async def get_report_status():
    if not PROMPTS_FILE.exists():
        return {"mtime": 0}
    return {"mtime": PROMPTS_FILE.stat().st_mtime}

def main():
    port = int(os.environ.get("PORT", 8082))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
