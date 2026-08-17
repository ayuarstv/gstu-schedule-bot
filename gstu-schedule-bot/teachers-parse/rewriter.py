import json
import hashlib
from pathlib import Path

teachers_file = Path("teachers.json")
teachers_link_file = Path("teachers_link.json")

if not teachers_link_file.exists():
    print("Файл teachers_link.json не найден")
    exit(1)

# загружаем teachers_link.json
with open(teachers_link_file, "r", encoding="utf-8") as f:
    try:
        teachers_link = json.load(f)
    except json.JSONDecodeError:
        print("Ошибка в формате JSON")
        exit(1)

# создаем новый словарь с grades, average, slug и hash
new_data = {}
for teacher, slug in teachers_link.items():
    # создаем полный MD5-хеш (32 символа)
    full_hash = hashlib.md5(teacher.encode("utf-8")).hexdigest()
    new_data[teacher] = {
        "grades": {},
        "average": 0.0,
        "slug": slug,
        "hash": full_hash
    }

# сортируем по алфавиту
new_data = dict(sorted(new_data.items(), key=lambda x: x[0]))

# сохраняем в teachers.json
with open(teachers_file, "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print(f"Файл teachers.json создан заново для {len(new_data)} преподавателей с slug и hash")
