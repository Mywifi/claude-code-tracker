import ipaddress
import socket
import logging

logger = logging.getLogger(__name__)

def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private/local."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False

def check_dns_private(host: str) -> tuple[bool, str]:
    """Check if a host resolves to a private IP."""
    try:
        ip = socket.gethostbyname(host)
        return is_private_ip(ip), ip
    except socket.gaierror:
        return False, ""
