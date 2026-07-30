# Dental Appointment Telegram Bot

A Telegram appointment bot built with **Python + aiogram 3** for booking dental services online.

## Features

**Clients:**
- Book an appointment: service → doctor → date → time → full name → phone → confirmation
- View own appointments
- Cancel an appointment
- Admin notifications on new bookings and cancellations

**Administrator:**
- View today's appointments
- View upcoming appointments
- Receive booking and cancellation alerts

## Clinic settings

- Services: Consultation, Cleaning, Cavity Treatment, Tooth Extraction
- Doctors: John Smith, Emily Johnson, Michael Brown, Olivia Davis (update in `config.py`)
- Hours: 09:00–17:00, closed on Sundays
- Interval: 45 minutes
- Bookings available for up to 14 days ahead

## Quick start (local)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file:
```bash
BOT_TOKEN=your_token_from_BotFather
ADMIN_IDS=808010571
```

3. Run the bot:
```bash
python main.py
```

## PostgreSQL support

Set `DATABASE_URL` in your `.env` if you want to use an external PostgreSQL database. Otherwise, the bot will use a local SQLite database by default.

## Deploy to Railway (recommended)

1. Sign up at [railway.app](https://railway.app).
2. Create a new project and deploy from GitHub, or use an empty service and upload the repository.
3. Add environment variables:
   - `BOT_TOKEN` = your bot token
   - `ADMIN_IDS` = 808010571
   - `DATABASE_URL` = your PostgreSQL connection URL (optional)
4. Set the start command to:
   - `python main.py`
5. Deploy.

## Change doctors / services

Open `config.py` and update the `SERVICES` and `DOCTORS` lists.

## Project structure

```
bot__telegram/
├── main.py              # Entry point
├── config.py            # Configuration
├── database.py          # Database layer
├── states.py            # FSM states
├── keyboards.py         # Keyboard layout helpers
├── handlers/            # Message and callback handlers
│   ├── user.py          # User booking flow
│   └── admin.py         # Admin interface
├── requirements.txt
└── .env.example
```

## Important

- The SQLite database is created automatically (`clinic.db`).
- On Railway, data is persisted between restarts by default.
- For higher production load, switch to PostgreSQL.
