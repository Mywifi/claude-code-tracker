import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_report(input_file: Path, output_file: Path):
    """
    Deprecated: The reporter now uses a decoupled frontend that fetches JSON data directly.
    This function is kept for backward compatibility but does nothing.
    """
    logger.debug("generate_report called (deprecated). Data is now served dynamically.")

def main():
    print("Reporter is now decoupled. Use proxy.py to serve the report.")

if __name__ == "__main__":
    main()
