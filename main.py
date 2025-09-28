#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import os
from colorama import Fore, Style, init
import sys
import random

init(autoreset=True)

ASCII_ART = Fore.GREEN + r"""
________________ ______________  ________.___. ___ ___             ____________________________    _____ __________ 
\__    ___/  _  \\______   \   \/  /\__  |   |/   |   \           /   _____/\_   ___ \______   \  /  _  \\______   \
  |    | /  /_\  \|     ___/\     /  /   |   /    ~    \  ______  \_____  \ /    \  \/|       _/ /  /_\  \|     ___/
  |    |/    |    \    |    /     \  \____   \    Y    / /_____/  /        \\     \___|    |   \/    |    \    |    
  |____|\____|__  /____|   /___/\  \ / ______|\___|_  /          /_______  / \______  /____|_  /\____|__  /____|    
                \/               \_/ \/             \/                   \/         \/       \/         \/          
""" + Style.RESET_ALL

THREADS = 100 
proxy_sources = {
    "socks4": [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    ],
    "socks5": [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/hookzof/socks5_list/refs/heads/master/proxy.txt",
    ],
}

results_dir = "results"
test_url = "https://httpbin.org/ip"  
timeout = 6

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36",
]

os.makedirs(results_dir, exist_ok=True)

async def fetch_proxies_from_urls(urls, timeout_sec=10):
    """Скачать и вернуть список прокси (строки) из набора URL-ов."""
    out = []
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession(headers=headers) as session:
        for url in urls:
            try:
                async with session.get(url, timeout=timeout_sec) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        for line in text.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            out.append(line)
            except Exception:
                continue
    return out

def save_result_sync(fname: str, line: str):
    path = os.path.join(results_dir, fname)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

def show_progress(done, total, good, bad, bar_len=30):
    percent = int((done / total) * 100) if total else 0
    filled = int(bar_len * percent // 100)
    bar = "#" * filled + "-" * (bar_len - filled)
    sys.stdout.write(
        f"\r{Fore.YELLOW}[{bar}] {percent:3d}% | "
        f"{Fore.GREEN}GOOD: {good} "
        f"{Fore.RED}BAD: {bad} "
        f"{Fore.CYAN}TOTAL: {done}/{total}"
    )
    sys.stdout.flush()

async def check_proxy_socks(proxy: str, ptype: str, lock, stats):
    """
    Проверяет один SOCKS прокси (ptype == 'socks4' или 'socks5').
    stats — dict с ключами done, good, bad, total
    lock — asyncio.Lock для синхронизации записи и обновления stats
    """
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    proxy_url = f"{ptype}://{proxy}"
    try:
        connector = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            async with session.get(test_url, timeout=timeout) as resp:
                if resp.status == 200:
                    async with lock:
                        stats["good"] += 1
                        save_result_sync(f"{ptype}.txt", proxy)
                else:
                    async with lock:
                        stats["bad"] += 1
                        save_result_sync(f"bad_{ptype}.txt", proxy)
    except Exception:
        async with lock:
            stats["bad"] += 1
            save_result_sync(f"bad_{ptype}.txt", proxy)
    finally:
        async with lock:
            stats["done"] += 1
            show_progress(stats["done"], stats["total"], stats["good"], stats["bad"])

async def main():
    print(ASCII_ART)

    socks4_list = await fetch_proxies_from_urls(proxy_sources.get("socks4", []))
    socks5_list = await fetch_proxies_from_urls(proxy_sources.get("socks5", []))

    socks4_list = list(dict.fromkeys([p.strip() for p in socks4_list if p and ":" in p]))
    socks5_list = list(dict.fromkeys([p.strip() for p in socks5_list if p and ":" in p]))

    all_proxies = [("socks4", p) for p in socks4_list] + [("socks5", p) for p in socks5_list]
    total = len(all_proxies)

    open(os.path.join(results_dir, "socks4.txt"), "w", encoding="utf-8").close()
    open(os.path.join(results_dir, "socks5.txt"), "w", encoding="utf-8").close()
    open(os.path.join(results_dir, "bad_socks4.txt"), "w", encoding="utf-8").close()
    open(os.path.join(results_dir, "bad_socks5.txt"), "w", encoding="utf-8").close()

    print(Fore.YELLOW + f"Найдено SOCKS4: {len(socks4_list)}, SOCKS5: {len(socks5_list)}. Всего: {total}")

    if total == 0:
        print(Fore.RED + "Нет прокси для проверки. Проверь источники." + Style.RESET_ALL)
        return

    # stats и lock
    stats = {"done": 0, "good": 0, "bad": 0, "total": total}
    lock = asyncio.Lock()

    sem = asyncio.Semaphore(THREADS)
    tasks = []

    # создаём задачи
    for ptype, proxy in all_proxies:
        async def sem_task(pt=ptype, pr=proxy):
            async with sem:
                await check_proxy_socks(pr, pt, lock, stats)
        tasks.append(asyncio.create_task(sem_task()))

    # начальный прогресс
    show_progress(0, total, 0, 0)

    # ждём завершения
    await asyncio.gather(*tasks)

    # финал
    print()  # newline
    print(Fore.CYAN + "[+] Сканирование завершено." + Style.RESET_ALL)
    print(Fore.GREEN + f"Рабочие: {stats['good']}" + Style.RESET_ALL + " | " +
          Fore.RED + f"Нерабочие: {stats['bad']}" + Style.RESET_ALL)
    print(f"Файлы в папке: {os.path.abspath(results_dir)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n" + Fore.YELLOW + "[!] Прервано пользователем." + Style.RESET_ALL)

