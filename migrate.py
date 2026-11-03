import sqlite3

conn = sqlite3.connect('commerce.db')
cursor = conn.cursor()

# 1. Add delivery_file_url to products if missing
try:
    cursor.execute("ALTER TABLE products ADD COLUMN delivery_file_url TEXT DEFAULT 'https://example.com/demo-download.pdf'")
    print("Added column delivery_file_url to products.")
except sqlite3.OperationalError as e:
    print("Column status:", e)

# 2. Ensure orders table exists
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
print("Migration complete.")
