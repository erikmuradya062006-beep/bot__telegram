import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "808010571").split(",") if x.strip()]

# Клиника
CLINIC_NAME = "Стоматологическая клиника"

# Услуги
SERVICES = [
    "Консультация",
    "Чистка",
    "Лечение кариеса",
    "Удаление зуба",
]

# Врачи
DOCTORS = [
    "Иванов Алексей Сергеевич",
    "Петрова Мария Ивановна",
    "Сидоров Дмитрий Андреевич",
    "Козлова Анна Викторовна",
]

# Рабочие часы
WORK_START_HOUR = 9
WORK_END_HOUR = 17
SLOT_MINUTES = 45
MAX_DAYS_AHEAD = 14
# Воскресенье = 6 (в Python weekday())
CLOSED_WEEKDAYS = [6]  # только воскресенье
