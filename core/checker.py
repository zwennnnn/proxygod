import asyncio
import time
import aiohttp
import random
from aiohttp_socks import ProxyConnector
from .models import Proxy, Protocol

# Multiple judges to avoid rate limiting and false negatives
JUDGES = [
    "http://httpbin.org/ip",
    "http://www.google.com/humans.txt", # Very reliable
    "http://detectportal.firefox.com/success.txt", # Extremely fast and high uptime
    "http://www.cloudflare.com/cdn-cgi/trace", # Cloudflare robust check
]
TIMEOUT = 10

async def check_single_proxy(proxy: Proxy) -> tuple[Proxy, bool, float]:
    """
    Checks a single proxy.
    Returns: (Proxy, is_live, latency_ms)
    """
    start_time = time.time()
    # Randomly select a judge for each request to distribute load
    target_url = random.choice(JUDGES)
    
    try:
        connector = ProxyConnector.from_url(proxy.to_url())
        
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
            async with session.get(target_url, ssl=False) as response:
                if response.status == 200:
                    latency = (time.time() - start_time) * 1000
                    return proxy, True, latency
    except Exception:
        pass
        
    return proxy, False, 0.0

async def check_proxies_generator(proxies, concurrency=300):
    """
    Yields results as they complete.
    """
    sem = asyncio.Semaphore(concurrency)
    
    async def sem_worker(p):
        async with sem:
            return await check_single_proxy(p)

    tasks = [sem_worker(p) for p in proxies]
    
    for future in asyncio.as_completed(tasks):
        yield await future
