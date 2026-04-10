import os
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Conflict, Forbidden, NetworkError, TimedOut
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler
from telegram.ext import filters as f

from config import ADMIN_USER_ID, BOT_NAME, PAYMENT_QR_CODE, PREMIUM_PRICE, TELEGRAM_BOT_TOKEN
from database import (
    can_add_habit,
    can_add_reminder,
    complete_habit,
    complete_reminder,
    count_active_habits,
    count_active_reminders,
    create_habit,
    create_reminder,
    create_subscription_request,
    delete_habit,
    delete_reminder,
    get_due_reminders,
    get_habit_stats,
    get_or_create_user,
    get_pending_subscription_by_user,
    get_user,
    get_user_habits,
    get_user_reminders,
    mark_reminder_sent,
    update_subscription_screenshot,
)
from keyboards import (
    habit_actions_keyboard,
    habit_menu_keyboard,
    main_menu_keyboard,
    reminder_actions_keyboard,
    reminder_menu_keyboard,
    settings_keyboard,
    subscription_keyboard,
)
from models import SessionLocal, User

PAYMENT_SCREENSHOT_DIR = "payment_screenshots"


def get_display_name(user):
    if user.username:
        return f"@{user.username}"
    if user.full_name:
        return user.full_name
    return str(user.id)


def reset_flow(context):
    for key in [
        "flow",
        "reminder_description",
        "reminder_recurring",
        "habit_frequency",
        "awaiting_screenshot",
    ]:
        context.user_data.pop(key, None)


async def send_or_edit(update: Update, text: str, reply_markup=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def ensure_not_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return True

    db_user = get_user(user.id)
    if db_user and db_user.is_blocked:
        reason = f"\nReason: {db_user.blocked_reason}" if db_user.blocked_reason else ""
        if update.message:
            await update.message.reply_text(f"Your account is blocked from using this bot.{reason}")
        elif update.callback_query:
            await update.callback_query.answer("Blocked user", show_alert=True)
            await update.callback_query.edit_message_text(f"Your account is blocked from using this bot.{reason}")
        reset_flow(context)
        return False
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    reset_flow(context)

    text = f"Welcome to {BOT_NAME}.\n\n"
    text += "Apex helps you manage reminders, habits, progress tracking, settings, and premium access.\n\n"
    text += "Main features:\n"
    text += "- Smart reminders with exact-time notifications\n"
    text += "- Daily and weekly habit tracking\n"
    text += "- Progress dashboard and streak stats\n"
    text += "- Settings for reminder alerts and summaries\n"
    text += "- Premium payment and screenshot review\n\n"
    text += f"Current plan: {'Premium' if db_user.is_premium else 'Free'}"
    await send_or_edit(update, text, reply_markup=main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    text = f"{BOT_NAME} commands\n\n"
    text += "/start - Main menu\n"
    text += "/help - Help section\n"
    text += "/profile - Profile and limits\n"
    text += "/reminders - Reminder menu\n"
    text += "/habits - Habit menu\n"
    text += "/progress - Habit progress\n"
    text += "/settings - Notification settings\n"
    text += "/subscribe - Premium payment flow\n"
    text += "/cancel - Cancel current input flow"
    await send_or_edit(update, text, reply_markup=main_menu_keyboard())


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    reset_flow(context)
    await send_or_edit(update, "Current action cancelled.", reply_markup=main_menu_keyboard())


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_user(user.id) or get_or_create_user(user.id, user.username, user.full_name)

    text = "Your profile\n\n"
    text += f"Name: {user.full_name or 'N/A'}\n"
    text += f"Username: @{user.username or 'N/A'}\n"
    text += f"Plan: {'Premium' if db_user.is_premium else 'Free'}\n"
    text += f"Active reminders: {count_active_reminders(user.id)}\n"
    text += f"Active habits: {count_active_habits(user.id)}\n"
    text += f"Reminder alerts: {'On' if db_user.reminders_enabled else 'Off'}\n"
    text += f"Daily summary: {'On' if db_user.daily_summary_enabled else 'Off'}"
    await send_or_edit(update, text, reply_markup=main_menu_keyboard())


async def reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_user(user.id)
    text = "Reminder Center\n\n"
    text += f"Active reminders: {count_active_reminders(user.id)}\n"
    text += f"Plan limit: {'Unlimited' if db_user and db_user.is_premium else '5 reminders'}\n"
    text += "Create reminders like: Study, Coding, Workout, Meeting, Revision."
    await send_or_edit(update, text, reply_markup=reminder_menu_keyboard())


async def habits_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_user(user.id)
    text = "Habit Tracker\n\n"
    text += f"Active habits: {count_active_habits(user.id)}\n"
    text += f"Plan limit: {'Unlimited' if db_user and db_user.is_premium else '3 habits'}\n"
    text += "Track habits like Coding, Reading, Gym, Meditation, Practice."
    await send_or_edit(update, text, reply_markup=habit_menu_keyboard())


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    await progress_menu(update, context)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    await settings_menu(update, context)


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_user(user.id) or get_or_create_user(user.id, user.username, user.full_name)
    text = "Settings\n\n"
    text += f"Reminder alerts: {'On' if db_user.reminders_enabled else 'Off'}\n"
    text += f"Daily summary: {'On' if db_user.daily_summary_enabled else 'Off'}\n"
    text += f"Timezone: {db_user.timezone}\n\n"
    text += "Use the buttons below to toggle features."
    await send_or_edit(
        update,
        text,
        reply_markup=settings_keyboard(
            "On" if db_user.reminders_enabled else "Off",
            "On" if db_user.daily_summary_enabled else "Off",
        ),
    )


async def add_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    if not can_add_reminder(update.effective_user.id):
        await send_or_edit(
            update,
            "Free reminder limit reached. Upgrade to premium for more reminders.",
            reply_markup=subscription_keyboard(),
        )
        return

    context.user_data["flow"] = "add_reminder_description"
    await send_or_edit(update, "Send reminder description. Example: Study and coding session")


async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    if not can_add_habit(update.effective_user.id):
        await send_or_edit(
            update,
            "Free habit limit reached. Upgrade to premium for more habits.",
            reply_markup=subscription_keyboard(),
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Daily", callback_data="habit_freq_daily")],
            [InlineKeyboardButton("Weekly", callback_data="habit_freq_weekly")],
            [InlineKeyboardButton("Back", callback_data="habits")],
        ]
    )
    await send_or_edit(update, "Choose habit frequency.", reply_markup=keyboard)


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    reminders = get_user_reminders(update.effective_user.id)
    if not reminders:
        await send_or_edit(update, "No reminders found.", reply_markup=reminder_menu_keyboard())
        return

    chunks = ["Your reminders\n"]
    for reminder in reminders:
        recurrence = reminder.recurrence_type if reminder.is_recurring else "one-time"
        chunks.append(
            f"ID {reminder.id}\nTask: {reminder.description}\nTime: {reminder.reminder_datetime.strftime('%d/%m/%Y %I:%M %p')}\nType: {recurrence}\nStatus: {'Done' if reminder.is_completed else 'Active'}\n"
        )
    text = "\n".join(chunks)
    await send_or_edit(update, text, reply_markup=reminder_menu_keyboard())

    for reminder in reminders:
        if update.message:
            await update.message.reply_text(
                f"Reminder ID {reminder.id}: {reminder.description}",
                reply_markup=reminder_actions_keyboard(reminder.id),
            )
        elif update.callback_query:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Reminder ID {reminder.id}: {reminder.description}",
                reply_markup=reminder_actions_keyboard(reminder.id),
            )


async def list_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    habits = get_user_habits(update.effective_user.id)
    if not habits:
        await send_or_edit(update, "No habits found.", reply_markup=habit_menu_keyboard())
        return

    chunks = ["Your habits\n"]
    for habit in habits:
        chunks.append(
            f"ID {habit.id}\nHabit: {habit.description}\nFrequency: {habit.frequency}\nCurrent streak: {habit.current_streak}\nBest streak: {habit.best_streak}\n"
        )
    text = "\n".join(chunks)
    await send_or_edit(update, text, reply_markup=habit_menu_keyboard())

    for habit in habits:
        if update.message:
            await update.message.reply_text(
                f"Habit ID {habit.id}: {habit.description}",
                reply_markup=habit_actions_keyboard(habit.id),
            )
        elif update.callback_query:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Habit ID {habit.id}: {habit.description}",
                reply_markup=habit_actions_keyboard(habit.id),
            )


async def progress_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    habits = get_user_habits(update.effective_user.id)
    if not habits:
        await send_or_edit(update, "No habits tracked yet.", reply_markup=main_menu_keyboard())
        return

    lines = ["Progress Dashboard", ""]
    for habit in habits:
        stats = get_habit_stats(habit.id) or {"current_streak": 0, "best_streak": 0, "total_completions": 0}
        lines.append(
            f"{habit.description}\n- Frequency: {habit.frequency}\n- Current streak: {stats['current_streak']}\n- Best streak: {stats['best_streak']}\n- Total completions: {stats['total_completions']}\n"
        )
    await send_or_edit(update, "\n".join(lines), reply_markup=main_menu_keyboard())


async def subscribe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    db_user = get_user(user.id)
    if db_user and db_user.is_premium:
        await send_or_edit(update, "Premium is already active.", reply_markup=main_menu_keyboard())
        return

    text = f"Premium Plan\n\nPrice: Rs. {PREMIUM_PRICE}/month\n\n"
    text += "Benefits:\n- Unlimited reminders\n- Unlimited habits\n- Faster support\n- Better productivity tracking\n\n"
    text += "Tap Subscribe Now, pay with QR, then send screenshot."
    await send_or_edit(update, text, reply_markup=subscription_keyboard())


async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    user = query.from_user
    db_user = get_user(user.id)
    if db_user and db_user.is_premium:
        await query.edit_message_text("Premium is already active.")
        return

    request = create_subscription_request(user.id, user.username, PREMIUM_PRICE)
    context.user_data["awaiting_screenshot"] = request.id
    reset_keys = ["flow", "reminder_description", "reminder_recurring", "habit_frequency"]
    for key in reset_keys:
        context.user_data.pop(key, None)

    text = f"Payment request created.\nRequest ID: {request.id}\nAmount: Rs. {PREMIUM_PRICE}\n\n"
    text += "After payment, send screenshot in this chat."

    if PAYMENT_QR_CODE and os.path.exists(PAYMENT_QR_CODE):
        with open(PAYMENT_QR_CODE, "rb") as qr_file:
            await context.bot.send_photo(chat_id=user.id, photo=qr_file, caption="Scan this QR and complete payment.")
    else:
        text += "\n\nQR image is not configured yet. Add a valid PAYMENT_QR_CODE path in .env."

    await query.edit_message_text(text)


async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    user = update.effective_user
    request_id = context.user_data.get("awaiting_screenshot")
    if not request_id:
        pending = get_pending_subscription_by_user(user.id)
        if pending:
            request_id = pending.id
            context.user_data["awaiting_screenshot"] = request_id
    if not request_id:
        return

    photo = update.message.photo[-1] if update.message.photo else None
    document = update.message.document
    if document and document.mime_type and not document.mime_type.startswith("image/"):
        await update.message.reply_text("Please send screenshot as image only.")
        return
    if not photo and not document:
        return

    os.makedirs(PAYMENT_SCREENSHOT_DIR, exist_ok=True)
    tg_file = await (photo.get_file() if photo else document.get_file())
    extension = ".jpg"
    if document and document.file_name and "." in document.file_name:
        extension = os.path.splitext(document.file_name)[1] or extension
    file_path = os.path.join(PAYMENT_SCREENSHOT_DIR, f"payment_{user.id}_{request_id}{extension}")
    await tg_file.download_to_drive(file_path)
    update_subscription_screenshot(request_id, file_path)
    context.user_data.pop("awaiting_screenshot", None)
    await update.message.reply_text("Payment screenshot received. Admin review pending.", reply_markup=main_menu_keyboard())

    if ADMIN_USER_ID:
        caption = f"Payment screenshot\nRequest ID: {request_id}\nUser: {get_display_name(user)}\nTelegram ID: {user.id}"
        try:
            with open(file_path, "rb") as image_file:
                if photo:
                    await context.bot.send_photo(chat_id=ADMIN_USER_ID, photo=image_file, caption=caption)
                else:
                    await context.bot.send_document(chat_id=ADMIN_USER_ID, document=image_file, caption=caption)
        except Exception as exc:
            print(f"Admin screenshot forward failed: {exc}")


async def process_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    flow = context.user_data.get("flow")
    text = (update.message.text or "").strip()
    if not flow:
        return

    if flow == "add_reminder_description":
        if not text:
            await update.message.reply_text("Reminder description cannot be empty.")
            return
        context.user_data["reminder_description"] = text
        context.user_data["flow"] = "add_reminder_recurring"
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("One Time", callback_data="reminder_type_once")],
                [InlineKeyboardButton("Repeat Daily", callback_data="reminder_type_daily")],
                [InlineKeyboardButton("Repeat Weekly", callback_data="reminder_type_weekly")],
            ]
        )
        await update.message.reply_text("Choose reminder type.", reply_markup=keyboard)
        return

    if flow == "add_reminder_datetime":
        try:
            reminder_dt = datetime.strptime(text, "%d/%m/%Y %I:%M %p")
        except ValueError:
            try:
                reminder_dt = datetime.strptime(text, "%d/%m/%Y %H:%M")
            except ValueError:
                await update.message.reply_text("Use DD/MM/YYYY HH:MM or DD/MM/YYYY HH:MM AM/PM")
                return

        if reminder_dt <= datetime.now():
            await update.message.reply_text("Reminder time must be in the future.")
            return

        recurrence_type = context.user_data.get("reminder_recurring")
        reminder = create_reminder(
            update.effective_user.id,
            context.user_data.get("reminder_description", "Reminder"),
            reminder_dt,
            is_recurring=recurrence_type in {"daily", "weekly"},
            recurrence_type=recurrence_type,
        )
        reset_flow(context)
        if not reminder:
            await update.message.reply_text("Reminder creation failed.", reply_markup=main_menu_keyboard())
            return
        await update.message.reply_text(
            f"Reminder created successfully.\n\nTask: {reminder.description}\nTime: {reminder.reminder_datetime.strftime('%d/%m/%Y %I:%M %p')}\nType: {reminder.recurrence_type or 'one-time'}",
            reply_markup=main_menu_keyboard(),
        )
        return

    if flow == "add_habit_description":
        frequency = context.user_data.get("habit_frequency")
        if not frequency:
            reset_flow(context)
            await update.message.reply_text("Habit frequency missing. Start again.", reply_markup=main_menu_keyboard())
            return
        if not text:
            await update.message.reply_text("Habit description cannot be empty.")
            return
        habit = create_habit(update.effective_user.id, text, frequency)
        reset_flow(context)
        if not habit:
            await update.message.reply_text("Habit could not be created.", reply_markup=main_menu_keyboard())
            return
        await update.message.reply_text(
            f"Habit created.\n\nHabit: {habit.description}\nFrequency: {habit.frequency}",
            reply_markup=main_menu_keyboard(),
        )


async def complete_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    habit_id = int(query.data.split("_")[-1])
    habit = complete_habit(habit_id, query.from_user.id)
    if not habit:
        await query.edit_message_text("Habit completion failed.")
        return
    await query.edit_message_text(f"Habit completed. Current streak: {habit.current_streak}")


async def delete_habit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    habit_id = int(query.data.split("_")[-1])
    habit = delete_habit(habit_id)
    await query.edit_message_text("Habit deleted." if habit else "Habit delete failed.")


async def complete_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    reminder_id = int(query.data.split("_")[-1])
    reminder = complete_reminder(reminder_id)
    await query.edit_message_text("Reminder completed." if reminder else "Reminder completion failed.")


async def delete_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    reminder_id = int(query.data.split("_")[-1])
    reminder = delete_reminder(reminder_id)
    await query.edit_message_text("Reminder deleted." if reminder else "Reminder delete failed.")


async def toggle_user_setting(user_id, field_name):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return None
        current_value = getattr(user, field_name)
        setattr(user, field_name, not current_value)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


async def reminder_dispatcher(context: ContextTypes.DEFAULT_TYPE):
    due_reminders = get_due_reminders(datetime.now())
    for reminder in due_reminders:
        user = get_user(reminder.user_id)
        if not user or not user.reminders_enabled:
            mark_reminder_sent(reminder.id)
            continue

        message = (
            f"Reminder time is on.\n\n"
            f"Task: {reminder.description}\n"
            f"Scheduled time: {reminder.reminder_datetime.strftime('%I:%M %p')}\n"
            f"Message from {BOT_NAME}: {reminder.description} now."
        )
        try:
            await context.bot.send_message(chat_id=reminder.user_id, text=message)
        except (TimedOut, NetworkError):
            continue
        except Forbidden:
            mark_reminder_sent(reminder.id)
            continue
        mark_reminder_sent(reminder.id)


async def daily_summary_dispatcher(context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.daily_summary_enabled.is_(True)).all()
        for user in users:
            reminders = get_user_reminders(user.telegram_id)
            habits = get_user_habits(user.telegram_id)
            text = "Daily Apex Summary\n\n"
            text += f"Active reminders: {len(reminders)}\n"
            text += f"Active habits: {len(habits)}\n"
            if reminders:
                next_reminder = reminders[0]
                text += f"Next reminder: {next_reminder.description} at {next_reminder.reminder_datetime.strftime('%I:%M %p')}\n"
            if habits:
                top_habit = habits[0]
                text += f"Keep going on: {top_habit.description}\n"
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text=text)
            except (TimedOut, NetworkError, Forbidden):
                continue
    finally:
        db.close()


async def post_init(application: Application):
    if application.job_queue is not None:
        application.job_queue.run_repeating(reminder_dispatcher, interval=30, first=10, name="reminder_dispatcher")
        application.job_queue.run_repeating(daily_summary_dispatcher, interval=21600, first=30, name="daily_summary")
    else:
        print('JobQueue not available. Install with: pip install "python-telegram-bot[job-queue]"')


async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_not_blocked(update, context):
        return
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "reminders":
        await reminders_menu(update, context)
    elif data == "habits":
        await habits_menu(update, context)
    elif data == "progress":
        await progress_menu(update, context)
    elif data == "profile":
        await profile_command(update, context)
    elif data == "premium":
        await subscribe_menu(update, context)
    elif data == "settings":
        await settings_menu(update, context)
    elif data == "back_main":
        await start_command(update, context)
    elif data == "add_reminder":
        await add_reminder_start(update, context)
    elif data == "add_habit":
        await add_habit_start(update, context)
    elif data == "list_reminders":
        await list_reminders(update, context)
    elif data == "list_habits":
        await list_habits(update, context)
    elif data == "subscribe_click":
        await subscribe_callback(update, context)
    elif data == "habit_freq_daily":
        context.user_data["habit_frequency"] = "daily"
        context.user_data["flow"] = "add_habit_description"
        await query.edit_message_text("Send habit description for daily habit.")
    elif data == "habit_freq_weekly":
        context.user_data["habit_frequency"] = "weekly"
        context.user_data["flow"] = "add_habit_description"
        await query.edit_message_text("Send habit description for weekly habit.")
    elif data == "reminder_type_once":
        context.user_data["reminder_recurring"] = None
        context.user_data["flow"] = "add_reminder_datetime"
        await query.edit_message_text("Send reminder date and time. Example: 10/04/2026 09:00 PM")
    elif data == "reminder_type_daily":
        context.user_data["reminder_recurring"] = "daily"
        context.user_data["flow"] = "add_reminder_datetime"
        await query.edit_message_text("Send first reminder date and time. It will repeat daily.")
    elif data == "reminder_type_weekly":
        context.user_data["reminder_recurring"] = "weekly"
        context.user_data["flow"] = "add_reminder_datetime"
        await query.edit_message_text("Send first reminder date and time. It will repeat weekly.")
    elif data == "toggle_reminders":
        await toggle_user_setting(query.from_user.id, "reminders_enabled")
        await settings_menu(update, context)
    elif data == "toggle_daily_summary":
        await toggle_user_setting(query.from_user.id, "daily_summary_enabled")
        await settings_menu(update, context)
    elif data.startswith("complete_habit_"):
        await complete_habit_callback(update, context)
    elif data.startswith("delete_habit_"):
        await delete_habit_callback(update, context)
    elif data.startswith("complete_reminder_"):
        await complete_reminder_callback(update, context)
    elif data.startswith("delete_reminder_"):
        await delete_reminder_callback(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")


def create_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("reminders", reminders_menu))
    app.add_handler(CommandHandler("habits", habits_menu))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("subscribe", subscribe_menu))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler((f.PHOTO | f.Document.IMAGE) & ~f.COMMAND, handle_payment_screenshot))
    app.add_handler(MessageHandler(f.TEXT & ~f.COMMAND, process_text_input))
    app.add_error_handler(error_handler)
    return app


def run_bot():
    app = create_bot()
    print(f"{BOT_NAME} is starting...")
    try:
        app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    except Conflict:
        print("Bot instance conflict: another bot process is already using this token. Stop the old process and run again.")


if __name__ == "__main__":
    run_bot()
