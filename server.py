import os
import sqlite3
import razorpay
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from db import init_db

load_dotenv()

key_id = os.getenv("RAZORPAY_KEY_ID", "")
key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
client = razorpay.Client(auth=(key_id, key_secret)) if (key_id and key_secret) else None

app = FastAPI(title="FastCommerce Engine")
DB_NAME = "commerce.db"

def seed_default_store():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM merchants WHERE slug = 'codecraft'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO merchants (store_name, slug, email, platform_fee_percent) VALUES (?, ?, ?, ?)",
                ("CodeCraft Store", "codecraft", "support@codecraft.io", 5.0)
            )
            merchant_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO products (merchant_id, title, price_rupees, delivery_file_url) VALUES (?, ?, ?, ?)",
                (merchant_id, "FastAPI Boilerplate Kit", 499, "https://github.com")
            )
            conn.commit()

@app.on_event("startup")
def startup():
    init_db()
    seed_default_store()

class CreateStorePayload(BaseModel):
    store_name: str
    slug: str
    email: str
    product_title: str
    price: int

class VerifyPaymentPayload(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    product_id: int

@app.get("/")
@app.get("/merchant")
@app.get("/dashboard")
@app.get("/dashboard.html")
def merchant_dashboard():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    return HTMLResponse("<h2>dashboard.html not found on server</h2>", status_code=404)

@app.post("/api/create-store")
def create_store(payload: CreateStorePayload):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO merchants (store_name, slug, email) VALUES (?, ?, ?)",
                (payload.store_name, payload.slug.lower(), payload.email)
            )
            merchant_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO products (merchant_id, title, price_rupees) VALUES (?, ?, ?)",
                (merchant_id, payload.product_title, payload.price)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Store URL slug already taken.")
    
    return {"store_url": f"/store/{payload.slug.lower()}"}

@app.get("/store/{slug}", response_class=HTMLResponse)
def get_store(slug: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.store_name, p.id, p.title, p.price_rupees, m.platform_fee_percent
            FROM merchants m
            JOIN products p ON m.id = p.merchant_id
            WHERE m.slug = ?
            LIMIT 1
        """, (slug.lower(),))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Store '{slug}' not found.")

    store_name, prod_id, prod_title, price, fee_percent = row
    merchant_share = int(price * (1 - (fee_percent / 100.0)))
    platform_cut = price - merchant_share

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{store_name}</title>
        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
        <style>
            body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8fafc; margin: 0; }}
            .card {{ background: white; padding: 32px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); width: 340px; text-align: center; }}
            button {{ background: #0284c7; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; }}
            .delivery-box {{ display: none; margin-top: 20px; padding: 16px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; }}
            .delivery-box a {{ color: #047857; font-weight: bold; text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="card" id="product-card">
            <span style="color:#64748b; font-size:12px; text-transform:uppercase;">Store: {store_name}</span>
            <h2 style="margin: 12px 0;">{prod_title}</h2>
            <h1 style="color: #0f172a;">₹{price}</h1>
            <button id="buy-btn">Buy Now</button>
            <p style="font-size:11px; color:#94a3b8; margin-top:16px;">Platform Fee: {fee_percent}% (₹{platform_cut}) | Merchant: ₹{merchant_share}</p>
            
            <div id="delivery" class="delivery-box">
                <h3 style="color:#065f46; margin: 0 0 8px;">🎉 Thank You!</h3>
                <p style="font-size:13px; color:#047857; margin:0 0 12px;">Your payment was verified successfully.</p>
                <a id="download-link" href="#" target="_blank">📥 Access Your Product Here</a>
            </div>
        </div>

        <script>
            document.getElementById('buy-btn').onclick = async function() {{
                const res = await fetch('/api/order/{prod_id}', {{ method: 'POST' }});
                const data = await res.json();
                
                if (!res.ok) {{
                    alert(data.detail || "Error generating order");
                    return;
                }}
                
                const rzp = new Razorpay({{
                    "key": data.key_id,
                    "amount": data.amount,
                    "currency": "INR",
                    "name": "{store_name}",
                    "description": "{prod_title}",
                    "order_id": data.order_id,
                    "handler": async function(response) {{
                        const verifyRes = await fetch('/api/verify-and-fulfill', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature,
                                product_id: {prod_id}
                            }})
                        }});
                        const result = await verifyRes.json();
                        if (result.success) {{
                            document.getElementById('buy-btn').style.display = 'none';
                            const deliveryBox = document.getElementById('delivery');
                            const dlLink = document.getElementById('download-link');
                            dlLink.href = result.download_url;
                            deliveryBox.style.display = 'block';
                        }} else {{
                            alert("Payment verification failed.");
                        }}
                    }}
                }});
                rzp.open();
            }};
        </script>
    </body>
    </html>
    """

@app.post("/api/order/{product_id}")
def create_dynamic_order(product_id: int):
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured.")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.title, p.price_rupees, m.store_name, m.platform_fee_percent
            FROM products p
            JOIN merchants m ON p.merchant_id = m.id
            WHERE p.id = ?
        """, (product_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    prod_title, price, store_name, fee_percent = row
    total_paise = price * 100
    platform_cut = int(total_paise * (fee_percent / 100.0))
    merchant_share = total_paise - platform_cut

    order = client.order.create({
        "amount": total_paise,
        "currency": "INR",
        "receipt": f"rcpt_p_{product_id}",
        "notes": {
            "platform_fee_paise": str(platform_cut),
            "merchant_share_paise": str(merchant_share),
            "store_name": store_name
        }
    })

    return {
        "order_id": order["id"],
        "key_id": key_id,
        "amount": total_paise
    }

@app.post("/api/verify-and-fulfill")
def verify_and_fulfill(payload: VerifyPaymentPayload):
    if not client:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured.")

    verify_data = {
        'razorpay_order_id': payload.razorpay_order_id,
        'razorpay_payment_id': payload.razorpay_payment_id,
        'razorpay_signature': payload.razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(verify_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.price_rupees, COALESCE(p.delivery_file_url, 'https://github.com'), m.platform_fee_percent
            FROM products p
            JOIN merchants m ON p.merchant_id = m.id
            WHERE p.id = ?
        """, (payload.product_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Product not found")

        price, delivery_url, fee_percent = row
        platform_cut = round(price * (fee_percent / 100.0), 2)
        merchant_share = round(price - platform_cut, 2)

        cursor.execute("""
            INSERT INTO orders (order_id, payment_id, product_id, amount_paid_rupees, platform_fee_rupees, merchant_share_rupees, status)
            VALUES (?, ?, ?, ?, ?, ?, 'paid')
        """, (payload.razorpay_order_id, payload.razorpay_payment_id, payload.product_id, price, platform_cut, merchant_share))
        conn.commit()

    return {
        "success": True,
        "download_url": delivery_url
    }

@app.get("/analytics/{slug}", response_class=HTMLResponse)
def merchant_analytics(slug: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, store_name FROM merchants WHERE slug = ?", (slug.lower(),))
        merchant = cursor.fetchone()
        if not merchant:
            raise HTTPException(status_code=404, detail="Store not found")
            
        merchant_id, store_name = merchant

        cursor.execute("""
            SELECT 
                COUNT(o.id),
                COALESCE(SUM(o.amount_paid_rupees), 0),
                COALESCE(SUM(o.merchant_share_rupees), 0),
                COALESCE(SUM(o.platform_fee_rupees), 0)
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE p.merchant_id = ? AND o.status = 'paid'
        """, (merchant_id,))
        total_orders, gross_rev, net_payout, total_fees = cursor.fetchone()

        cursor.execute("""
            SELECT o.order_id, o.payment_id, p.title, o.amount_paid_rupees, o.merchant_share_rupees
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE p.merchant_id = ? AND o.status = 'paid'
            ORDER BY o.id DESC LIMIT 10
        """, (merchant_id,))
        recent_orders = cursor.fetchall()

    rows_html = "".join([
        f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>₹{r[3]}</td><td style='color:#16a34a; font-weight:600;'>₹{r[4]}</td></tr>"
        for r in recent_orders
    ]) or "<tr><td colspan='5' style='text-align:center; color:#94a3b8;'>No orders yet</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{store_name} Analytics</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; margin: 0; padding: 40px 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            h1 {{ color: #0f172a; margin-bottom: 24px; }}
            .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
            .stat-title {{ font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }}
            .stat-value {{ font-size: 26px; font-weight: 700; color: #0f172a; margin-top: 8px; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
            th, td {{ padding: 14px 16px; text-align: left; font-size: 14px; }}
            th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
            tr:not(:last-child) td {{ border-bottom: 1px solid #f1f5f9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{store_name} Sales Dashboard</h1>
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-title">Total Orders</div>
                    <div class="stat-value">{total_orders}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Gross Volume</div>
                    <div class="stat-value">₹{gross_rev}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Net Merchant Share</div>
                    <div class="stat-value" style="color: #16a34a;">₹{net_payout}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Platform Fees</div>
                    <div class="stat-value" style="color: #6366f1;">₹{total_fees}</div>
                </div>
            </div>

            <h2 style="color:#1e293b; font-size: 18px; margin-bottom: 12px;">Recent Completed Orders</h2>
            <table>
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Payment ID</th>
                        <th>Product</th>
                        <th>Gross</th>
                        <th>Net Share</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """