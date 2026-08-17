import aiohttp
import asyncio
from collections import defaultdict
from groupes import groups
import uuid
from cache import cache
import random
from os import getenv
from dotenv import load_dotenv
from datetime import datetime, date, timedelta

BASE_URL = "https://sc.gstu.by/api/schedules/group"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
]


async def fetch_schedule(group_name: str) -> dict: # тут запрашиваем
    # генерируем новый tid для каждого запроса
    tid = uuid.uuid4().hex
    headers = get_headers()
    headers["X-Id"] = tid
    headers["Cookie"] = f"_tid={tid}"
    headers["Referer"] = f"https://sc.gstu.by/group/{groups[group_name]}"

    load_dotenv()
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{BASE_URL}/{groups[group_name]}", 
                               timeout=15,
                                proxy=getenv('PROXY') # get proxy from env
                               ) as resp:
            resp.raise_for_status()
            return await resp.json()
        
async def fetch_schedule_cached(group_name: str) -> dict: # Снаачало проверяем есть ли в кеше, потом уже запрашиваем
    key = f"schedule:{group_name}"
    data = await cache.get_json(key)
    
    if data:
        return data
    
    try:
        fresh = await fetch_schedule(group_name)
        await cache.set_json(key, fresh, expire=60 * 60 * 24 * 2) 
        return fresh
    except HTTPStatusError as e:
        if data and e.responce.status_code == 403:
            return data
        raise 


async def fetch_teacher_schedule(slug: str) -> dict:
    """Запрос расписания преподавателя напрямую из API ГГТУ."""
    tid = uuid.uuid4().hex
    headers = get_headers()
    headers["X-Id"] = tid
    headers["Cookie"] = f"_tid={tid}"
    headers["Referer"] = f"https://sc.gstu.by/teacher/{slug}"

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"https://sc.gstu.by/api/schedules/teacher/{slug}",
                               timeout=15,
                               proxy=getenv("PROXY")) as resp:
            resp.raise_for_status()
            return await resp.json()


async def get_teacher_schedule_cached(slug: str) -> dict:
    """Кэшируем расписание преподавателя."""
    key = f"teacher_schedule:{slug}"
    data = await cache.get_json(key)
    if data:
        return data

    fresh = await fetch_teacher_schedule(slug)
    if fresh:
        await cache.set_json(key, fresh, expire=60 * 60 * 24 * 2)  # 2 дня
    return fresh

def get_headers(): # Рандомизируем хедерсы
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": random.choice(["ru-RU,ru;q=0.9", "ru,en;q=0.8", "en-US,en;q=0.7"]),
        "Connection": "keep-alive",
    }

# TODO: Перенести методы которые не относятся к запросам к API в utils



# Пример использования
async def main():
    pass
    # data = await fetch_schedule_cached("АП-11")
    #pprint(data)
    # print(pretty_schedule_str(data))


if __name__ == "__main__":
    asyncio.run(main())