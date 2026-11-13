import aiosqlite
import time

DB_PATH = "tamagotchi.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 100,
                satiety INTEGER DEFAULT 100,
                happiness INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                is_alive INTEGER DEFAULT 1,
                last_update INTEGER
            )
        """)
        await db.commit()


async def get_pet(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pets WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_pet(user_id: int, name: str, pet_type: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        now = int(time.time())
        await db.execute(
            """INSERT OR REPLACE INTO pets
               (user_id, name, type, level, xp, coins, satiety, happiness, energy, is_alive, last_update)
               VALUES (?, ?, ?, 1, 0, 100, 100, 100, 100, 1, ?)""",
            (user_id, name, pet_type, now)
        )
        await db.commit()
    return await get_pet(user_id)


async def calculate_ticks(user_id: int) -> dict:
    pet = await get_pet(user_id)
    if not pet:
        return None
    if not pet["is_alive"]:
        return pet

    now = int(time.time())
    diff_minutes = (now - pet["last_update"]) // 60

    if diff_minutes > 0:
        new_satiety = max(0, pet["satiety"] - (diff_minutes * 2))
        new_happiness = max(0, pet["happiness"] - (diff_minutes * 2))
        new_energy = max(0, pet["energy"] - (diff_minutes * 1))

        earned_coins = 0
        if pet["satiety"] > 40 and pet["happiness"] > 40:
            earned_coins = diff_minutes * 2
        new_coins = pet["coins"] + earned_coins

        new_alive = 1
        if new_satiety == 0 and new_happiness == 0:
            new_alive = 0

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """UPDATE pets
                   SET satiety = ?, happiness = ?, energy = ?, coins = ?, is_alive = ?, last_update = ? 
                   WHERE user_id = ?""",
                (new_satiety, new_happiness, new_energy, new_coins, new_alive, now, user_id)
            )
            await db.commit()
        return await get_pet(user_id)
    return pet


async def process_action(user_id: int, action: str) -> dict:
    pet = await get_pet(user_id)
    if not pet or not pet["is_alive"]:
        return pet

    satiety, happiness, energy, coins, xp, level = (
        pet["satiety"],
        pet["happiness"],
        pet["energy"],
        pet["coins"],
        pet["xp"],
        pet["level"],
    )

    if action == "feed" and coins >= 15:
        coins -= 15
        satiety = min(100, satiety + 25)
        xp += 10
    elif action == "play" and energy >= 20:
        energy -= 20
        happiness = min(100, happiness + 30)
        xp += 15
    elif action == "sleep":
        energy = min(100, energy + 40)
        satiety = max(0, satiety - 10)
        xp += 5

    if xp >= level * 100:
        xp -= (level * 100)
        level += 1

    async with aiosqlite.connect(DB_PATH) as db:
        now = int(time.time())
        await db.execute(
            """UPDATE pets
               SET satiety = ?, happiness = ?, energy = ?, coins = ?, xp = ?, level = ?, last_update = ?
               WHERE user_id = ?""",
            (satiety, happiness, energy, coins, xp, level, now, user_id)
        )
        await db.commit()
    return await get_pet(user_id)
