import re
import aiohttp
import asyncio
import json
from typing import List, Set, Union
from rich.console import Console
from .models import Proxy, Protocol

console = Console()

PROXY_REGEX = re.compile(r'(?:^|\s)((?:[0-9]{1,3}\.){3}[0-9]{1,3})(?::|\s+)([0-9]{1,5})(?:\s|$)')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def fetch_url(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception:
        pass
    return ""

def parse_proxies_from_text(content: str, default_protocol: Protocol) -> List[Proxy]:
    proxies = []
    
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "proxies" in data and isinstance(data["proxies"], list):
            for p_data in data["proxies"]:
                if "ip" in p_data and "port" in p_data:
                    proto_str = p_data.get("protocol", "").lower()
                    protocol = default_protocol
                    
                    if "socks4" in proto_str:
                        protocol = Protocol.SOCKS4
                    elif "socks5" in proto_str:
                        protocol = Protocol.SOCKS5
                    elif "http" in proto_str:
                        protocol = Protocol.HTTP
                        
                    proxies.append(Proxy(
                        ip=p_data["ip"], 
                        port=int(p_data["port"]), 
                        protocol=protocol
                    ))
            return proxies
    except json.JSONDecodeError:
        pass 
    
    matches = PROXY_REGEX.findall(content)
    for ip, port in matches:
        proxies.append(Proxy(ip=ip, port=int(port), protocol=default_protocol))
    
    return proxies

async def fetch_all_proxies(providers_file: str, advanced_url: str = None) -> List[Proxy]:
    all_proxies: Set[Proxy] = set()
    
    urls_by_protocol = {
        Protocol.HTTP: [],
        Protocol.SOCKS4: [],
        Protocol.SOCKS5: []
    }
    
    current_protocol = Protocol.HTTP 
    
    try:
        with open(providers_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            if "socks4" in lower_line and "api" in lower_line:
                current_protocol = Protocol.SOCKS4
            elif "socks5" in lower_line and "api" in lower_line:
                current_protocol = Protocol.SOCKS5
            elif "http" in lower_line and "api" in lower_line:
                current_protocol = Protocol.HTTP
            elif "socks4" in lower_line:
                current_protocol = Protocol.SOCKS4
            elif "socks5" in lower_line:
                current_protocol = Protocol.SOCKS5
            elif "http" in lower_line:
                current_protocol = Protocol.HTTP
            
            if line.startswith("http"):
                if "advanced.name" in line:
                    continue 
                
                urls_by_protocol[current_protocol].append(line)
                
    except FileNotFoundError:
        console.log("[bold red]Providers file not found![/bold red]")
        return []

    if advanced_url:
        base_url = advanced_url.split('?')[0]
        urls_by_protocol[Protocol.HTTP].append(f"{base_url}?type=http")
        urls_by_protocol[Protocol.SOCKS4].append(f"{base_url}?type=socks4")
        urls_by_protocol[Protocol.SOCKS5].append(f"{base_url}?type=socks5")

    async with aiohttp.ClientSession() as session:
        tasks = []
        
        async def fetch_and_parse(url, protocol):
             content = await fetch_url(session, url)
             found = parse_proxies_from_text(content, protocol)
             return found
        
        for protocol, urls in urls_by_protocol.items():
            for url in urls:
                tasks.append(fetch_and_parse(url, protocol))
                
        results = await asyncio.gather(*tasks)
        
        for proxy_list in results:
            for p in proxy_list:
                all_proxies.add(p)
                
    return list(all_proxies)
