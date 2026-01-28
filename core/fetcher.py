import re
import aiohttp
import asyncio
import json
import time
from typing import List, Set, Union
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from .models import Proxy, Protocol

console = Console()

PROXY_REGEX = re.compile(r'(?:^|\s)((?:[0-9]{1,3}\.){3}[0-9]{1,3})(?::|\s+)([0-9]{1,5})(?:\s|$)')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def fetch_url(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=HEADERS, timeout=30) as response:
            if response.status == 200:
                return await response.text()
    except Exception:
        pass
    return ""

def parse_proxies_from_text(content: str, default_protocol: Protocol) -> List[Proxy]:
    proxies = []
    
    try:
        data = json.loads(content)
        
        # Geonode API support
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
             for p_data in data["data"]:
                if "ip" in p_data and "port" in p_data:
                    # Geonode returns protocols as a list, e.g. ["socks4"]
                    proto_list = p_data.get("protocols", [])
                    if isinstance(proto_list, list) and len(proto_list) > 0:
                        proto_str = proto_list[0].lower()
                    else:
                        proto_str = str(p_data.get("protocol", "")).lower()

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

        # ProxyScrape and others
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


async def fetch_proxydb(session: aiohttp.ClientSession, on_progress=None) -> List[Proxy]:
    """Scrapes proxydb.net pages for proxies."""
    import random
    
    base_url = "https://proxydb.net/?country=&offset={offset}"
    max_offset = 3340
    step = 30
    delay_range = (1.0, 2.5)
    
    proxydb_proxies = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://proxydb.net/"
    }
    
    for offset in range(0, max_offset + 1, step):
        url = base_url.format(offset=offset)
        retries = 3
        success = False
        batch_proxies = []

        for attempt in range(retries):
            try:
                async with session.get(url, headers=headers, timeout=20) as response:
                    if response.status == 200:
                        content = await response.text()
                        rows = re.findall(r'<tr>(.*?)</tr>', content, re.DOTALL)
                        
                        for row in rows:
                            cells = row.split('</td>')
                            if len(cells) < 3: continue
                            
                            ip_m = re.search(r'(?:>|")(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:<|")', cells[0])
                            if not ip_m: continue
                            ip = ip_m.group(1)
                            
                            port_m = re.search(r'<a[^>]*>(\d+)</a>', cells[1])
                            if not port_m: port_m = re.search(r'>(\d+)<', cells[1])
                            if not port_m: continue
                            port = int(port_m.group(1))
                            
                            p_cell = cells[2]
                            protocol = Protocol.HTTP
                            if "socks5" in p_cell.lower(): protocol = Protocol.SOCKS5
                            elif "socks4" in p_cell.lower(): protocol = Protocol.SOCKS4
                            
                            p = Proxy(ip=ip, port=port, protocol=protocol)
                            proxydb_proxies.append(p)
                            batch_proxies.append(p)
                        
                        success = True
                        break
                    elif response.status == 429:
                        wait = 30 * (attempt + 1)
                        if on_progress:
                           
                            pass
                        await asyncio.sleep(wait)
                        continue
                    else:
                        break
            except Exception:
                await asyncio.sleep(2)
        
        if on_progress:
            try:
                await on_progress(batch_proxies, offset, max_offset)
            except Exception:
                pass

        if not success:
            pass
        
        await asyncio.sleep(random.uniform(*delay_range))

    return proxydb_proxies

async def fetch_free_proxy_list(session: aiohttp.ClientSession, on_progress=None) -> List[Proxy]:
    """Scrapes free-proxy-list.net for proxies."""
    targets = [
        {"url": "https://free-proxy-list.net/tr/socks-proxy.html", "type": "socks"},
        {"url": "https://free-proxy-list.net/tr/", "type": "http"}
    ]
    
    found_proxies = []
    
    for target in targets:
        url = target["url"]
        p_type = target["type"]
        
        try:
            async with session.get(url, headers=HEADERS, timeout=20) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Extract table body
                    tbody_match = re.search(r'<tbody>(.*?)</tbody>', content, re.DOTALL)
                    if not tbody_match: continue
                    tbody = tbody_match.group(1)
                    
                    rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)
                    
                    batch_proxies = []
                    for row in rows:
                        cols = re.findall(r'<td.*?>(.*?)</td>', row)
                        if not cols: continue
                        
                        if p_type == "socks" and len(cols) >= 5:
                            ip = cols[0]
                            port = cols[1]
                            version = cols[4].lower()
                            
                            protocol = Protocol.SOCKS4
                            if "socks5" in version: protocol = Protocol.SOCKS5
                            elif "socks4" in version: protocol = Protocol.SOCKS4
                            
                            p = Proxy(ip=ip, port=int(port), protocol=protocol)
                            found_proxies.append(p)
                            batch_proxies.append(p)
                            
                        elif p_type == "http" and len(cols) >= 7:
                            ip = cols[0]
                            port = cols[1]
                            protocol = Protocol.HTTP
                            
                            p = Proxy(ip=ip, port=int(port), protocol=protocol)
                            found_proxies.append(p)
                            batch_proxies.append(p)

                    if on_progress:
                        await on_progress(batch_proxies, 0, 0)
                        
        except Exception:
            pass
            
    return found_proxies


async def fetch_all_proxies(providers_file: str, advanced_url: str = None) -> List[Proxy]:
    with open("fetch_stats.txt", "w", encoding="utf-8") as f:
        f.write(f"--- Proxy Fetch Stats ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---\n")

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
            if not line: continue
            
            lower_line = line.lower()
            if "socks4" in lower_line and "api" in lower_line: current_protocol = Protocol.SOCKS4
            elif "socks5" in lower_line and "api" in lower_line: current_protocol = Protocol.SOCKS5
            elif "http" in lower_line and "api" in lower_line: current_protocol = Protocol.HTTP
            elif "socks4" in lower_line: current_protocol = Protocol.SOCKS4
            elif "socks5" in lower_line: current_protocol = Protocol.SOCKS5
            elif "http" in lower_line: current_protocol = Protocol.HTTP
            
            if line.startswith("http"):
                if "advanced.name" in line: continue 
                urls_by_protocol[current_protocol].append(line)
                
    except FileNotFoundError:
        console.log("[bold red]Providers file not found![/bold red]")
        return []

    if advanced_url:
        base_url = advanced_url.split('?')[0]
        urls_by_protocol[Protocol.HTTP].append(f"{base_url}?type=http")
        urls_by_protocol[Protocol.SOCKS4].append(f"{base_url}?type=socks4")
        urls_by_protocol[Protocol.SOCKS5].append(f"{base_url}?type=socks5")

    # State for UI
    total_fetched = 0
    start_time = time.time()
    
    current_live_update = None

    async def master_callback(new_proxies, current_step=0, total_steps=0):
        nonlocal total_fetched
        added_count = 0
        for p in new_proxies:
            if p not in all_proxies:
                all_proxies.add(p)
                added_count += 1
        
        total_fetched = len(all_proxies)
        
        # ETR Calculation
        eta_str = "Calculating..."
        pct = 0
        if total_steps > 0:
            if current_step > 0:
                elapsed = time.time() - start_time
                ratio = current_step / total_steps
                if ratio > 0:
                    est_total = elapsed / ratio
                    rem = est_total - elapsed
                    if rem < 0: rem = 0
                    m, s = divmod(int(rem), 60)
                    eta_str = f"{m}m {s}s"
            
            pct = int((current_step/total_steps)*100)

        # Update UI if Live is active
        if current_live_update:
            content = f"[bold green]Total Unique Proxies: {total_fetched}[/bold green]"
            if total_steps > 0:
                content += f"\n[yellow]Scanning ProxyDB & FreeProxyList: {pct}%[/yellow]"
                content += f"\n[cyan]Estimated Time Remaining: {eta_str}[/cyan]"
            else:
                 # Initial phase
                 content += f"\n[dim]Scanning standard providers...[/dim]"
            
            current_live_update(Panel(content, title="Scraping Proxies", border_style="cyan"))

    async with aiohttp.ClientSession() as session:
        
        # Wrapped standard fetcher
        async def fetch_standard(url, protocol):
             content = await fetch_url(session, url)
             found = parse_proxies_from_text(content, protocol)
             
             # Log stats
             msg = f"Fetched {len(found)} from {url}" if found else f"Failed {url}"
             with open("fetch_stats.txt", "a", encoding="utf-8") as f:
                 f.write(msg + "\n")
                 
             # Update global
             await master_callback(found, 0, 0)
             return found

        # Prepare Tasks
        tasks = []
        for protocol, urls in urls_by_protocol.items():
            for url in urls:
                tasks.append(fetch_standard(url, protocol))
        
        # Add ProxyDB task with callback
        tasks.append(fetch_proxydb(session, master_callback))
        # Add FreeProxyList task
        tasks.append(fetch_free_proxy_list(session, master_callback))

        # Launch UI and Tasks
        with Live(console=console, transient=True, refresh_per_second=4) as live:
             current_live_update = live.update
             
             live.update(Panel("[cyan]Initializing Scrape...[/cyan]", title="Scraping", border_style="cyan"))
             
             # Run all tasks parallel
             await asyncio.gather(*tasks)
             
             # Final
             live.update(Panel(f"[bold green]Scraping Complete![/bold green]\nTotal Unique: {len(all_proxies)}", border_style="green"))
             await asyncio.sleep(1.5)

    return list(all_proxies)
