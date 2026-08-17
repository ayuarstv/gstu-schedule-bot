import os
import json
import hashlib
from typing import Optional, Tuple, List, Dict

DB_FILE = "db.json"
TEACHERS_FILE = "teachers.json"


class Database:
    def __init__(self):
        self.users = {}
        self.teachers = {}
        self.grades = {}
        self.settings = {}  # {user_id: {"notify": true}}
        self._load()

    def _load(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.users = data.get("users", {})
                self.grades = data.get("grades", {})
                self.settings = data.get("settings", {})

        if os.path.exists(TEACHERS_FILE):
            with open(TEACHERS_FILE, "r", encoding="utf-8") as f:
                teachers_data = json.load(f)
                if isinstance(teachers_data, list):
                    self.teachers = {
                        name: {"slug": "", "hash": hashlib.md5(name.encode()).hexdigest()}
                        for name in teachers_data
                    }
                elif isinstance(teachers_data, dict):
                    self.teachers = teachers_data

    def _save(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"users": self.users, "grades": self.grades, "settings": self.settings},
                f, ensure_ascii=False, indent=2
            )

    async def init(self):
        pass

    async def set_group(self, user_id: int, group: str) -> None:
        self.users[str(user_id)] = group
        self._save()

    async def get_group(self, user_id: int) -> Optional[str]:
        return self.users.get(str(user_id))

    async def delete_user(self, user_id: int) -> None:
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            self._save()

    async def all_users(self) -> Dict[str, str]:
        return self.users

    async def ensure_user(self, user_id: int, group: str = None) -> None:
        if str(user_id) not in self.users:
            self.users[str(user_id)] = group or ""
            self._save()

    async def user_exists(self, user_id: int) -> bool:
        return str(user_id) in self.users

    # --- notifications ---
    async def get_notify(self, user_id: int) -> bool:
        return self.settings.get(str(user_id), {}).get("notify", False)

    async def set_notify(self, user_id: int, value: bool):
        if str(user_id) not in self.settings:
            self.settings[str(user_id)] = {}
        self.settings[str(user_id)]["notify"] = value
        self._save()

    # --- teachers ---
    async def add_teacher_rating(self, full_name: str, grade: int, user_id: int) -> Tuple[float, int]:
        return 0.0, 0

    async def get_teacher_rating(self, full_name: str) -> Tuple[float, int]:
        return 0.0, 0

    async def search_teachers(self, search: str) -> List[Dict]:
        results = []
        search_lower = search.lower()
        for name, data in self.teachers.items():
            if search_lower in name.lower():
                results.append({
                    "full_name": name,
                    "slug": data.get("slug", ""),
                    "hash": data.get("hash", hashlib.md5(name.encode()).hexdigest())
                })
        return results[:50]

    async def get_teacher_name_by_hash(self, hash_id: str) -> Optional[str]:
        for name, data in self.teachers.items():
            if data.get("hash") == hash_id:
                return name
        return None

    async def get_teacher_by_hash(self, hash_id: str) -> Optional[Dict]:
        for name, data in self.teachers.items():
            if data.get("hash") == hash_id:
                return {"full_name": name, **data}
        return None

    async def get_teacher_by_name(self, fullname: str) -> str | None:
        data = self.teachers.get(fullname)
        return data.get("slug") if data else None


db = Database()