import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL or "sqlite:///commerce.db")

def init_db():
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS merchants (
                    id SERIAL PRIMARY KEY,
                    store_name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    platform_fee_percent FLOAT DEFAULT 5.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    merchant_id INTEGER REFERENCES merchants(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    price_rupees INTEGER NOT NULL,
                    delivery_file_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(100) NOT NULL,
                    payment_id VARCHAR(100) NOT NULL,
                    product_id INTEGER REFERENCES products(id),
                    amount_paid_rupees FLOAT NOT NULL,
                    platform_fee_rupees FLOAT NOT NULL,
                    merchant_share_rupees FLOAT NOT NULL,
                    status VARCHAR(50) DEFAULT 'paid',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
        else:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS merchants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    platform_fee_percent REAL DEFAULT 5.0
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    merchant_id INTEGER REFERENCES merchants(id),
                    title TEXT NOT NULL,
                    price_rupees INTEGER NOT NULL,
                    delivery_file_url TEXT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    payment_id TEXT NOT NULL,
                    product_id INTEGER REFERENCES products(id),
                    amount_paid_rupees REAL NOT NULL,
                    platform_fee_rupees REAL NOT NULL,
                    merchant_share_rupees REAL NOT NULL,
                    status TEXT DEFAULT 'paid'
                );
            """))
