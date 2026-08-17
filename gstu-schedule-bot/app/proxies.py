import random
from pathlib import Path

PROXY_FILE = Path(__file__).resolve().parent / "proxies.txt"

def load_proxies(): # берем прокси из файла 
    if not PROXY_FILE.exists():
        return []
    with open(PROXY_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]
    return proxies

def get_random_proxy(): # выдаем любой прокси из кучи
    proxies = load_proxies()
    if not proxies:
        return None
    return random.choice(proxies)
