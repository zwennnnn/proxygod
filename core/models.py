from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Protocol(Enum):
    HTTP = "http"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

@dataclass
class Proxy:
    ip: str
    port: int
    protocol: Protocol
    username: Optional[str] = None
    password: Optional[str] = None
    
    def __hash__(self):
        return hash((self.ip, self.port, self.protocol))

    def to_url(self) -> str:
        """Returns the proxy URL for aiohttp/requests."""
        # Format: scheme://user:pass@host:port
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.ip}:{self.port}"

    def __str__(self):
        return f"{self.ip}:{self.port}"
