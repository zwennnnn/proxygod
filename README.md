# ProxyGod by zwennnnn

The Ultimate Proxy Scraper & Checker by zwennnnn.

## Features
- **Hacker Theme UI**: Powered by `rich`.
- **Async Speed**: Ultra-fast checking with `aiohttp` and reliable concurrency.
- **Smart Rotation**: Uses random judge servers (Google, Cloudflare, Firefox, Httpbin) to prevent rate-limiting and ensure false-free results.
- **Multi-Protocol**: Supports HTTP, SOCKS4, SOCKS5.
- **Smart Export**: Automatically saves live proxies to `output/`.

## Setup

1. Install Python (Make sure to check "Add Python to PATH" during installation).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the main script:
```bash
python main.py
```

- If you have an `advanced.name` daily link, paste it when prompted.
- Watch the magic happen!

## Understanding Results (Live vs Dead)

You might notice a high number of "Dead" proxies compared to "Live" ones (e.g., getting 300 live out of 20,000). **This is completely normal and expected.**

- **Strict Checking:** THIS TOOL DOES NOT JUST PING. It performs a **strict connection test** (making a real finding request to a judge server). Many proxies respond to ping but fail to forward data. We only give you proxies that **actually work**.
- **Public Nature:** Free public proxies are used by thousands of people simultaneously. They are short-lived, unstable, and often overloaded.
- **Quality > Quantity:** Finding 100-500 *truly working* proxies is far more valuable than a list of 10,000 "maybe working" IPs.

## Special Thanks

This project wouldn't be possible without these amazing open-source proxy providers:

- **[TheSpeedX](https://github.com/TheSpeedX/SOCKS-List)**
- **[monosans](https://github.com/monosans/proxy-list)**
- **[clarketm](https://github.com/clarketm/proxy-list)**
- **[iplocate](https://github.com/iplocate/free-proxy-list)**
- **[hookzof](https://github.com/hookzof/socks5_list)**
- **[ProxyScrape](https://proxyscrape.com/)**
- **[Advanced.name](https://advanced.name/)**

*And many more to come! New providers are added regularly to ensure the best results.*
