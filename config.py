import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

DATABASE_URL = "sqlite:///habitual.db"

PREMIUM_PRICE = 49

FREE_LIMIT_REMINDERS = 5
FREE_LIMIT_HABITS = 3

PAYMENT_QR_CODE = os.getenv("PAYMENT_QR_CODE", "")

BOT_NAME = "Habitual"
TEAM_NAME = "Apex Team"
DEVELOPER_NAME = "Apex Developer"