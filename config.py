import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "808010571").split(",") if x.strip()]

# External PostgreSQL URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Local SQLite fallback
DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.getenv("DB_PATH", os.path.join(DATA_DIR, "clinic.db"))

# Clinic
CLINIC_NAME = "Dental Care Clinic"

# Services
SERVICES = [
    "Consultation",
    "Cleaning",
    "Cavity Treatment",
    "Tooth Extraction",
]

# Doctors
DOCTORS = [
    "John Smith",
    "Emily Johnson",
    "Michael Brown",
    "Olivia Davis",
]

# Clinic working hours
WORK_START_HOUR = 9
WORK_END_HOUR = 17
SLOT_MINUTES = 45
MAX_DAYS_AHEAD = 14
# Sunday = 6 (Python weekday())
CLOSED_WEEKDAYS = [6]  # only Sunday
