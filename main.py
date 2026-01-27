import asyncio
import sys
import os
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from core.models import Proxy, Protocol
from core.fetcher import fetch_all_proxies
from core.checker import check_proxies_generator
from core.exporter import export_proxies
from ui.tui import Dashboard

console = Console()

def print_banner_simple():
    banner_text = """
    [bold green]
    ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗ ██████╗  ██████╗ ██████╗ 
    ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝██╔════╝ ██╔═══██╗██╔══██╗
    ██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ ██║  ███╗██║   ██║██║  ██║
    ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  ██║   ██║██║   ██║██║  ██║
    ██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║   ╚██████╔╝╚██████╔╝██████╔╝
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝ ╚═════╝ 
    [/bold green]
    [bold white]        The Ultimate Proxy Scraper & Checker by zwennnnn[/bold white]
    """
    console.print(Panel(banner_text, border_style="green", expand=False))

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

async def main():
    print_banner_simple()
    
    # Try to find providers.md in the bundle or local file system
    providers_path = get_resource_path(os.path.join("data", "providers.md"))
    
    if not os.path.exists(providers_path):
        # Fallback to local paths if bundle path fails (dev mode mixed)
        if os.path.exists("data/providers.md"):
            providers_path = "data/providers.md"
        elif os.path.exists("providers.md"):
            providers_path = "providers.md"
        else:
            console.print("[bold red]ERROR: providers.md not found![/bold red]")
            return

    console.print("\n[bold cyan]Setup[/bold cyan]")
    console.print("Please visit [link=https://advanced.name/freeproxy]https://advanced.name/freeproxy[/link] for daily rotating proxies.")
    advanced_url = console.input("[bold green]Paste the Advanced.name link here (Enter to skip): [/bold green]")

    console.print()
    with console.status("[bold yellow]Fetching proxies from providers...[/bold yellow]", spinner="dots"):
        proxies = await fetch_all_proxies(providers_path, advanced_url if advanced_url.strip() else None)
        
    console.print(f"[green]Successfully fetched {len(proxies)} unique proxies![/green]")
    if not proxies:
        return

    console.print("[yellow]Preparing to launch Checker Dashboard...[/yellow]")
    await asyncio.sleep(2) 

    dashboard = Dashboard()
    dashboard.total = len(proxies)
    
    live_proxies = []
    
    with Live(dashboard.layout, refresh_per_second=10, screen=True) as live:
        async for proxy, is_live, latency in check_proxies_generator(proxies):
            dashboard.add_log(proxy, is_live, latency)
            
            if is_live:
                dashboard.update(checked_increment=1, live_increment=1)
                live_proxies.append(proxy)
            else:
                dashboard.update(checked_increment=1, dead_increment=1)
                
    console.clear() 
    print_banner_simple()
    console.print(Panel(f"[bold white]Scan Complete![/bold white]\n\nChecked: {len(proxies)}\nLive: [green]{len(live_proxies)}[/green]", border_style="green"))
    
    if live_proxies:
        export_proxies(live_proxies, "output")
        console.print("[bold green]Proxies exported to the 'output' folder.[/bold green]")
        
        if sys.platform == 'win32':
             os.startfile(os.path.abspath("output"))
    else:
        console.print("[red]No live proxies found. Try updating providers.[/red]")

    console.input("[dim]Press Enter to exit...[/dim]")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    try:
        if sys.platform == 'win32':
             # Python 3.8+ on Windows defaults to ProactorEventLoop which is better
             pass 
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")
