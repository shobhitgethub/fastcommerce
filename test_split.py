import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

key_id = os.getenv("RAZORPAY_KEY_ID")
key_secret = os.getenv("RAZORPAY_KEY_SECRET")

if not key_id or not key_secret:
    print("Error: Missing RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET in .env")
    exit(1)

client = razorpay.Client(auth=(key_id, key_secret))

amount_rupees = 500
amount_paise = amount_rupees * 100
platform_fee_percent = 5.0
platform_fee = int(amount_paise * (platform_fee_percent / 100))
merchant_share = amount_paise - platform_fee

order_data = {
    "amount": amount_paise,
    "currency": "INR",
    "receipt": "receipt_order_001",
    "notes": {
        "store": "CodeCraft Store",
        "platform_fee_inr": str(platform_fee / 100),
        "merchant_share_inr": str(merchant_share / 100)
    }
}

order = client.order.create(data=order_data)
print(f"Order created successfully: {order['id']}")
print(f"Platform Fee retained: INR {platform_fee / 100}")
print(f"Merchant Payout: INR {merchant_share / 100}")
