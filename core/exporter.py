import os
from typing import List, Dict
from .models import Proxy, Protocol

def export_proxies(proxies: List[Proxy], output_dir: str = "output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Group by protocol
    by_protocol: Dict[Protocol, List[Proxy]] = {
        Protocol.HTTP: [],
        Protocol.SOCKS4: [],
        Protocol.SOCKS5: []
    }
    
    for p in proxies:
        by_protocol[p.protocol].append(p)
        
    # Write files
    for proto, plist in by_protocol.items():
        filename = f"{proto.value}.txt"
        path = os.path.join(output_dir, filename)
        
        with open(path, "w", encoding='utf-8') as f:
            for p in plist:
                f.write(f"{str(p)}\n")
        
    # Write a summary "all_live.txt"
    with open(os.path.join(output_dir, "all.txt"), "w", encoding='utf-8') as f:
        for p in proxies:
            f.write(f"{p.to_url()}\n")
            
    print(f"Exported {len(proxies)} proxies to {output_dir}")
