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

# Progress constants for long-running providers (used for unified % display)
PROXYDB_MAX_OFFSET = 3340
PROXYDB_STEP = 30
PROXYDB_STEPS = len(range(0, PROXYDB_MAX_OFFSET + 1, PROXYDB_STEP))

FREEPROXYDB_PAGES = 25

LUMIPROXY_PAGES = 29
LUMIPROXY_BASE = (
    "https://api.lumiproxy.com/web_v1/free-proxy/list"
    "?page_size=60&page={page}&language=en-us"
)

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


async def fetch_proxydb(
    session: aiohttp.ClientSession,
    on_progress=None,
    progress_offset: int = 0,
    total_steps: int = 0,
) -> List[Proxy]:
    """Scrapes proxydb.net pages for proxies."""
    import random
    
    base_url = "https://proxydb.net/?country=&offset={offset}"
    delay_range = (1.0, 2.5)
    
    proxydb_proxies = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://proxydb.net/"
    }
    
    for step_index, offset in enumerate(
        range(0, PROXYDB_MAX_OFFSET + 1, PROXYDB_STEP), start=1
    ):
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
        
        if on_progress and total_steps > 0:
            try:
                global_step = progress_offset + step_index
                await on_progress(
                    batch_proxies,
                    current_step=global_step,
                    total_steps=total_steps,
                    provider="ProxyDB",
                    page=step_index,
                    page_max=PROXYDB_STEPS,
                )
            except Exception:
                pass

        if not success:
            pass
        
        await asyncio.sleep(random.uniform(*delay_range))

    return proxydb_proxies

FREEPROXYDB_BASE = (
    "https://freeproxydb.com/api/proxy/subscribe"
    "?country=&protocol=&anonymity=&speed=0,60&https=0"
    "&page_index={page_index}&page_size=100&subscribe_format=original"
)

async def fetch_freeproxydb(
    session: aiohttp.ClientSession,
    on_progress=None,
    progress_offset: int = 0,
    total_steps: int = 0,
) -> List[Proxy]:
    all_proxies: List[Proxy] = []
    for page_index in range(1, FREEPROXYDB_PAGES + 1):
        url = FREEPROXYDB_BASE.format(page_index=page_index)
        try:
            content = await fetch_url(session, url)
            batch = []
            for line in content.splitlines():
                line = line.strip()
                if not line.lower().startswith("socks://"):
                    continue
                rest = line[7:]  # "socks://"
                if ":" not in rest:
                    continue
                try:
                    ip, port_str = rest.rsplit(":", 1)
                    port = int(port_str)
                    if 1 <= port <= 65535:
                        p = Proxy(ip=ip.strip(), port=port, protocol=Protocol.SOCKS5)
                        all_proxies.append(p)
                        batch.append(p)
                except (ValueError, TypeError):
                    continue
            if content:
                with open("fetch_stats.txt", "a", encoding="utf-8") as f:
                    f.write(f"FreeProxyDB page {page_index}: {len(batch)} proxies\n")
            if on_progress and total_steps > 0:
                try:
                    global_step = progress_offset + page_index
                    await on_progress(
                        batch,
                        current_step=global_step,
                        total_steps=total_steps,
                        provider="FreeProxyDB",
                        page=page_index,
                        page_max=FREEPROXYDB_PAGES,
                    )
                except Exception:
                    pass
        except Exception:
            pass
        if page_index < FREEPROXYDB_PAGES:
            await asyncio.sleep(1.5)
    return all_proxies

async def fetch_lumiproxy(
    session: aiohttp.ClientSession,
    on_progress=None,
    progress_offset: int = 0,
    total_steps: int = 0,
) -> List[Proxy]:
    """
    Fetches proxies from LumiProxy free-proxy API.
    Pages: 1..LUMIPROXY_PAGES, page_size=60, 5s delay between requests.
    """
    all_proxies: List[Proxy] = []

    for page in range(1, LUMIPROXY_PAGES + 1):
        url = LUMIPROXY_BASE.format(page=page)
        batch: List[Proxy] = []
        try:
            content = await fetch_url(session, url)
            if content:
                try:
                    data = json.loads(content)
                    items = (
                        data.get("data", {}).get("list", [])
                        if isinstance(data, dict)
                        else []
                    )
                    for item in items:
                        ip = item.get("ip")
                        port = item.get("port")
                        proto_num = item.get("protocol")
                        if not ip or not port:
                            continue

                        # LumiProxy protocol mapping guess:
                        # 4 -> SOCKS4, 8 -> SOCKS5, others -> HTTP
                        protocol = Protocol.HTTP
                        try:
                            if proto_num == 4:
                                protocol = Protocol.SOCKS4
                            elif proto_num == 8:
                                protocol = Protocol.SOCKS5
                        except Exception:
                            protocol = Protocol.HTTP

                        try:
                            p = Proxy(ip=str(ip), port=int(port), protocol=protocol)
                            all_proxies.append(p)
                            batch.append(p)
                        except (TypeError, ValueError):
                            continue
                except json.JSONDecodeError:
                    pass

            with open("fetch_stats.txt", "a", encoding="utf-8") as f:
                f.write(f"LumiProxy page {page}: {len(batch)} proxies\n")

            if on_progress and total_steps > 0:
                try:
                    global_step = progress_offset + page
                    await on_progress(
                        batch,
                        current_step=global_step,
                        total_steps=total_steps,
                        provider="LumiProxy",
                        page=page,
                        page_max=LUMIPROXY_PAGES,
                    )
                except Exception:
                    pass
        except Exception:
            pass

        if page < LUMIPROXY_PAGES:
            await asyncio.sleep(5)

    return all_proxies

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
                        await on_progress(
                            batch_proxies,
                            current_step=0,
                            total_steps=0,
                            provider="FreeProxyList",
                            page=None,
                            page_max=None,
                        )
                        
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

    # Progress configuration (for % and ETA)
    global_total_steps = PROXYDB_STEPS + FREEPROXYDB_PAGES + LUMIPROXY_PAGES

    # State for UI
    total_fetched = 0
    start_time = time.time()
    
    current_live_update = None

    # Track per-provider page progress for display
    provider_pages = {
        "ProxyDB": {"page": 0, "total": PROXYDB_STEPS},
        "FreeProxyDB": {"page": 0, "total": FREEPROXYDB_PAGES},
        "LumiProxy": {"page": 0, "total": LUMIPROXY_PAGES},
        "FreeProxyList": {"page": 0, "total": 0},
    }

    async def master_callback(
        new_proxies,
        current_step: int = 0,
        total_steps: int = 0,
        provider: str | None = None,
        page: int | None = None,
        page_max: int | None = None,
    ):
        nonlocal total_fetched
        added_count = 0
        for p in new_proxies:
            if p not in all_proxies:
                all_proxies.add(p)
                added_count += 1
        
        total_fetched = len(all_proxies)
        
        # Update per-provider page info
        if provider and provider in provider_pages:
            info = provider_pages[provider]
            if page is not None:
                info["page"] = page
            if page_max is not None and page_max > 0:
                info["total"] = page_max
        
        # ETR Calculation and % based on all providers together
        eta_str = "Calculating..."
        pct = 0
        # Sadece ProxyDB + FreeProxyDB + LumiProxy adımlarını hesaba kat
        done_steps = (
            provider_pages["ProxyDB"]["page"]
            + provider_pages["FreeProxyDB"]["page"]
            + provider_pages["LumiProxy"]["page"]
        )
        if global_total_steps > 0 and done_steps > 0:
            elapsed = time.time() - start_time
            ratio = done_steps / global_total_steps
            if ratio > 0:
                est_total = elapsed / ratio
                rem = est_total - elapsed
                if rem < 0:
                    rem = 0
                m, s = divmod(int(rem), 60)
                eta_str = f"{m}m {s}s"
            pct = int((done_steps / global_total_steps) * 100)

        # Update UI if Live is active
        if current_live_update:
            content = f"[bold green]Total Unique Proxies: {total_fetched}[/bold green]"
            if total_steps > 0:
                content += f"\n[yellow]Overall progress: {pct}%[/yellow]"
                content += f"\n[cyan]Estimated Time Remaining: {eta_str}[/cyan]"

                # Detailed provider status
                for name, info in provider_pages.items():
                    p_page = info.get("page", 0)
                    p_total = info.get("total", 0)
                    if p_total > 0 and p_page > 0:
                        content += f"\n[white]{name}[/white]: page {p_page}/{p_total}"
                    elif p_total > 0:
                        content += f"\n[white]{name}[/white]: waiting (0/{p_total})"
                    else:
                        content += f"\n[white]{name}[/white]: running"
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
                 
             # Update global (no effect on %)
             await master_callback(
                 found,
                 current_step=0,
                 total_steps=0,
                 provider="Standard",
                 page=None,
                 page_max=None,
             )
             return found

        # Prepare Tasks
        tasks = []
        for protocol, urls in urls_by_protocol.items():
            for url in urls:
                tasks.append(fetch_standard(url, protocol))
        
        # Progress offsets for long-running providers
        proxydb_offset = 0
        freeproxydb_offset = PROXYDB_STEPS
        lumiproxy_offset = PROXYDB_STEPS + FREEPROXYDB_PAGES
        
        # Add ProxyDB task with unified progress
        tasks.append(
            fetch_proxydb(
                session,
                master_callback,
                progress_offset=proxydb_offset,
                total_steps=global_total_steps,
            )
        )
        # Add FreeProxyList task (instant, no %)
        tasks.append(fetch_free_proxy_list(session, master_callback))
        # FreeProxyDB API: page_index 1-25, 100 per page, socks://ip:port
        tasks.append(
            fetch_freeproxydb(
                session,
                master_callback,
                progress_offset=freeproxydb_offset,
                total_steps=global_total_steps,
            )
        )
        # LumiProxy API: page 1-29, 60 per page, 5s delay
        tasks.append(
            fetch_lumiproxy(
                session,
                master_callback,
                progress_offset=lumiproxy_offset,
                total_steps=global_total_steps,
            )
        )

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
