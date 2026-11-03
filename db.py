import sqlite3

DB_NAME = "commerce.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Merchants
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        platform_fee_percent REAL DEFAULT 5.0
    );
    """)

    # 2. Products with Download / Delivery URL
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        price_rupees INTEGER NOT NULL,
        delivery_file_url TEXT DEFAULT 'https://example.com/demo-download.pdf',
        FOREIGN KEY (merchant_id) REFERENCES merchants (id)
    );
    """)

    # 3. Paid Orders Audit
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE NOT NULL,
        payment_id TEXT UNIQUE,
        product_id INTEGER,
        amount_paid_rupees INTEGER,
        platform_fee_rupees REAL,
        merchant_share_rupees REAL,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (product_id) REFERENCES products (id)
    );
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database updated with orders & fulfillment schema.")
