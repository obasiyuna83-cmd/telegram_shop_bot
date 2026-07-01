import aiosqlite
import os

DB_PATH = "shop.db"

async def init_db():
    """Инициализация базы данных и создание таблиц, если они не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image_url TEXT
            )
        """)
        
        # Таблица заказов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                status TEXT DEFAULT 'New',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)
        
        # Заполним тестовыми товарами, если таблица пуста
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute("""
                INSERT INTO products (name, description, price, image_url) VALUES 
                ('Курс по Python', 'Освойте разработку на Python с нуля за 3 месяца.', 4900.0, 'https://picsum.photos/400/300'),
                ('Telegram-бот под ключ', 'Разработка профессионального бота любой сложности.', 9900.0, 'https://picsum.photos/400/300'),
                ('Парсер сайтов в Excel', 'Автоматический сбор данных с любого сайта.', 3500.0, 'https://picsum.photos/400/300')
            """)
        
        await db.commit()

async def add_user(user_id: int, username: str):
    """Регистрация нового пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()

async def get_products():
    """Получение списка всех товаров."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products") as cursor:
            return await cursor.fetchall()

async def get_product_by_id(product_id: int):
    """Получение товара по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            return await cursor.fetchone()

async def create_order(user_id: int, product_id: int):
    """Создание нового заказа."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO orders (user_id, product_id) VALUES (?, ?)",
            (user_id, product_id)
        )
        await db.commit()

async def get_user_by_username(username: str):
    """Получение ID пользователя по его юзернейму."""
    async with aiosqlite.connect(DB_PATH) as db:
        username_clean = username.lstrip('@')
        async with db.execute(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?)", 
            (username_clean,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
