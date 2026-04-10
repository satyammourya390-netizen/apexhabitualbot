# Habitual - Telegram Bot

A Telegram bot for reminders and habit tracking with premium subscription support.

## Features

- Reminders (one-time and recurring)
- Habit tracking with streaks
- Progress visualization
- Premium subscription (₹49/month)
- Admin panel for subscription management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
   - Copy `config.example.py` to `config.py`
   - Add your Telegram Bot Token
   - Configure Admin ID

3. Run the bot:
```bash
python bot.py
```

4. Run admin panel (optional):
```bash
python admin.py
```

## Commands

- `/start` - Start the bot
- `/help` - Get help
- `/reminder` - Manage reminders
- `/habit` - Manage habits
- `/subscribe` - Subscribe to premium
- `/profile` - View profile and stats

## License

MIT