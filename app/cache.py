class Cache:
    def __init__(self):
        self._data = {}

    async def init(self):
        pass

    async def get_json(self, key: str):
        return self._data.get(key)

    async def set_json(self, key: str, value, expire: int = 604800):
        self._data[key] = value

cache = Cache()