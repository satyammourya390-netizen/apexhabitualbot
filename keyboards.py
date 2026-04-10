from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Reminders", callback_data="reminders")],
        [InlineKeyboardButton("Habits", callback_data="habits")],
        [InlineKeyboardButton("Progress", callback_data="progress")],
        [InlineKeyboardButton("Profile", callback_data="profile")],
        [InlineKeyboardButton("Premium", callback_data="premium")],
        [InlineKeyboardButton("Settings", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)


def reminder_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Add Reminder", callback_data="add_reminder")],
        [InlineKeyboardButton("My Reminders", callback_data="list_reminders")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def habit_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Add Habit", callback_data="add_habit")],
        [InlineKeyboardButton("My Habits", callback_data="list_habits")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard(reminder_status, daily_status):
    keyboard = [
        [InlineKeyboardButton(f"Reminder Alerts: {reminder_status}", callback_data="toggle_reminders")],
        [InlineKeyboardButton(f"Daily Summary: {daily_status}", callback_data="toggle_daily_summary")],
        [InlineKeyboardButton("Refresh Settings", callback_data="settings")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def reminder_actions_keyboard(reminder_id):
    keyboard = [
        [InlineKeyboardButton("Mark Done", callback_data=f"complete_reminder_{reminder_id}")],
        [InlineKeyboardButton("Delete", callback_data=f"delete_reminder_{reminder_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def habit_actions_keyboard(habit_id):
    keyboard = [
        [InlineKeyboardButton("Complete Today", callback_data=f"complete_habit_{habit_id}")],
        [InlineKeyboardButton("Delete", callback_data=f"delete_habit_{habit_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("Subscribe Now", callback_data="subscribe_click")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
