import aiohttp
import asyncio
import json
import os
from groupes import groups
from tqdm import tqdm  # <--- прогрессбар

BASE_URL = "https://sc.gstu.by/api/schedules/group"
TEACHERS_FILE = "teachers.json"


async def fetch_schedule(session: aiohttp.ClientSession, group_code: str) -> dict:
    url = f"{BASE_URL}/{group_code}"
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json()


def extract_teachers(data: dict) -> set[str]:
    teachers = set()
    for item in data["data"]["scheduleItems"]:
        for teacher in item.get("teachers", []):
            teachers.add(teacher["fullName"])  # можно поменять на shortName
    return teachers


def load_existing_teachers() -> set[str]:
    if os.path.exists(TEACHERS_FILE):
        with open(TEACHERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_teachers(teachers: set[str]):
    with open(TEACHERS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(teachers), f, ensure_ascii=False, indent=4)


async def main():
    headers = {"User-Agent": "Mozilla/5.0"}
    all_teachers = load_existing_teachers()

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for group_name, group_code in groups.items():
            tasks.append((group_name, fetch_schedule(session, group_code)))

        teachers_bar = tqdm(total=len(tasks), desc="Загрузка расписаний")

        for group_name, task in tasks:
            try:
                result = await task
                all_teachers |= extract_teachers(result)
            except Exception as e:
                print(f"⚠ Ошибка в {group_name}: {e}")
            teachers_bar.update(1)

        teachers_bar.close()

    save_teachers(all_teachers)
    print(f"Всего преподавателей: {len(all_teachers)}")
    print(f"Сохранено в {TEACHERS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
