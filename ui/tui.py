from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from datetime import datetime

class Dashboard:
    def __init__(self):
        self.layout = Layout()
        self.total = 0
        self.checked = 0
        self.live = 0
        self.dead = 0
        self.logs = [] 
        self.max_logs = 15
        
        self.layout.split(
            Layout(name="header", size=10),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="stats"),
            Layout(name="logs", ratio=2)
        )
        
        self.update_header()
        
    def update_header(self):
        banner_text = """
[bold green]
██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗ ██████╗  ██████╗ ██████╗ 
██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝██╔════╝ ██╔═══██╗██╔══██╗
██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ ██║  ███╗██║   ██║██║  ██║
██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  ██║   ██║██║   ██║██║  ██║
██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║   ╚██████╔╝╚██████╔╝██████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝ ╚═════╝ 
[/bold green]
[bold white]   The Ultimate Proxy Scraper & Checker by zwennnnn[/bold white]
"""
        self.layout["header"].update(Panel(Align.center(Text.from_markup(banner_text)), border_style="green"))

    def get_stats_panel(self):
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="bold white")
        
        table.add_row("Total Proxies", str(self.total))
        table.add_row("Checked", str(self.checked))
        table.add_row("Live", f"[green]{self.live}[/green]")
        table.add_row("Dead", f"[red]{self.dead}[/red]")
        
        remaining = self.total - self.checked
        table.add_row("Remaining", str(remaining))
        
        success_rate = 0
        if self.checked > 0:
            success_rate = (self.live / self.checked) * 100
        table.add_row("Success Rate", f"{success_rate:.1f}%")

        return Panel(table, title="[bold yellow]Statistics[/bold yellow]", border_style="yellow")

    def get_logs_panel(self):
        log_table = Table(show_header=True, header_style="bold magenta", expand=True)
        log_table.add_column("Time", width=10)
        log_table.add_column("Status", width=10)
        log_table.add_column("Proxy", ratio=1)
        log_table.add_column("Latency", width=10)
        
        for log in self.logs[-self.max_logs:]:
            log_table.add_row(*log)
            
        return Panel(log_table, title="[bold blue]Live Logs[/bold blue]", border_style="blue")

    def add_log(self, proxy, is_live, latency):
        time_str = datetime.now().strftime("%H:%M:%S")
        status_str = "[green]LIVE[/green]" if is_live else "[red]DEAD[/red]"
        latency_str = f"{latency:.0f}ms" if is_live else "-"
        
        self.logs.append([time_str, status_str, str(proxy), latency_str])
        
    def update(self, checked_increment=0, live_increment=0, dead_increment=0):
        self.checked += checked_increment
        self.live += live_increment
        self.dead += dead_increment
        
        self.layout["stats"].update(self.get_stats_panel())
        self.layout["logs"].update(self.get_logs_panel())
        
        # Progress Bar Logic
        percent = 0
        if self.total > 0:
            percent = (self.checked / self.total) * 100
        bar_width = 50
        filled = int((percent / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        footer_text = f"[bold cyan]Progress:[/bold cyan] [{bar}] {percent:.1f}% ({self.checked}/{self.total})"
        self.layout["footer"].update(Panel(footer_text, border_style="white"))
        
        return self.layout
