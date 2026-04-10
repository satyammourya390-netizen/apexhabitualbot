from telegram import Update
from telegram.error import Conflict, Forbidden, NetworkError, TimedOut
from telegram.ext import Application, CommandHandler, ContextTypes

from config import ADMIN_USER_ID, BOT_NAME, TELEGRAM_BOT_TOKEN
from database import (
    approve_subscription,
    block_user,
    get_all_users,
    get_dashboard_stats,
    get_pending_subscriptions,
    get_user,
    reject_subscription,
    revoke_premium,
    search_user,
    unblock_user,
)


def is_admin(user_id):
    return bool(ADMIN_USER_ID and user_id == ADMIN_USER_ID)


async def ensure_admin(update: Update):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use admin commands.")
        return False
    return True


def parse_user_id(value):
    return int(value.strip())


async def notify_user(context: ContextTypes.DEFAULT_TYPE, user_id: int, message: str):
    try:
        await context.bot.send_message(chat_id=user_id, text=message)
    except (Forbidden, TimedOut, NetworkError):
        pass


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    text = f"{BOT_NAME} Master Admin Panel\n\n"
    text += "Subscription controls:\n"
    text += "/pending - View pending premium requests\n"
    text += "/approve <request_id> - Approve premium\n"
    text += "/reject <request_id> - Reject premium\n"
    text += "/dismisspremium <user_id> - Remove premium access\n\n"
    text += "User controls:\n"
    text += "/userinfo <user_id> - View full user profile\n"
    text += "/block <user_id> [reason] - Block a user\n"
    text += "/unblock <user_id> - Unblock a user\n"
    text += "/recentusers - List latest users\n\n"
    text += "Analytics:\n"
    text += "/users - Dashboard stats"
    await update.message.reply_text(text)


async def pending_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    pending = get_pending_subscriptions()
    if not pending:
        await update.message.reply_text("No pending subscriptions.")
        return

    lines = ["Pending premium requests", ""]
    for item in pending:
        lines.append(
            f"Request ID: {item.id}\nUser ID: {item.user_id}\nUsername: @{item.username or 'N/A'}\nAmount: Rs. {item.amount}\nCreated: {item.created_at.strftime('%d/%m/%Y %I:%M %p')}\nScreenshot: {item.screenshot_path or 'Not uploaded'}\nApprove: /approve {item.id}\nReject: /reject {item.id}\n"
        )
    await update.message.reply_text("\n".join(lines))


async def approve_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        request_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /approve <request_id>")
        return

    request = approve_subscription(request_id)
    if not request:
        await update.message.reply_text(f"Request {request_id} not found.")
        return

    await update.message.reply_text(f"Subscription {request_id} approved for user {request.user_id}.")
    await notify_user(context, request.user_id, "Your premium plan has been approved. Premium is now active.")


async def reject_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        request_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /reject <request_id>")
        return

    request = reject_subscription(request_id)
    if not request:
        await update.message.reply_text(f"Request {request_id} not found.")
        return

    await update.message.reply_text(f"Subscription {request_id} rejected.")
    await notify_user(context, request.user_id, "Your premium request was rejected. Please contact support or send a valid payment proof.")


async def dismiss_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        telegram_id = parse_user_id(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /dismisspremium <user_id>")
        return

    user = revoke_premium(telegram_id)
    if not user:
        await update.message.reply_text(f"User {telegram_id} not found.")
        return

    await update.message.reply_text(f"Premium removed for user {telegram_id}.")
    await notify_user(context, telegram_id, "Your premium access has been removed by admin.")


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        telegram_id = parse_user_id(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /block <user_id> [reason]")
        return

    if telegram_id == ADMIN_USER_ID:
        await update.message.reply_text("Master admin cannot be blocked.")
        return

    reason = " ".join(context.args[1:]).strip() or "Violation of policy"
    user = block_user(telegram_id, reason)
    if not user:
        await update.message.reply_text(f"User {telegram_id} not found.")
        return

    await update.message.reply_text(f"User {telegram_id} blocked. Reason: {reason}")
    await notify_user(context, telegram_id, f"Your account has been blocked by admin. Reason: {reason}")


async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        telegram_id = parse_user_id(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /unblock <user_id>")
        return

    user = unblock_user(telegram_id)
    if not user:
        await update.message.reply_text(f"User {telegram_id} not found.")
        return

    await update.message.reply_text(f"User {telegram_id} unblocked.")
    await notify_user(context, telegram_id, "Your account has been unblocked. You can use the bot again.")


async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    try:
        telegram_id = parse_user_id(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /userinfo <user_id>")
        return

    user = search_user(telegram_id)
    if not user:
        await update.message.reply_text(f"User {telegram_id} not found.")
        return

    text = "User profile\n\n"
    text += f"Telegram ID: {user.telegram_id}\n"
    text += f"Username: @{user.username or 'N/A'}\n"
    text += f"Full name: {user.full_name or 'N/A'}\n"
    text += f"Premium: {'Yes' if user.is_premium else 'No'}\n"
    text += f"Blocked: {'Yes' if user.is_blocked else 'No'}\n"
    text += f"Block reason: {user.blocked_reason or 'N/A'}\n"
    text += f"Reminder alerts: {'On' if user.reminders_enabled else 'Off'}\n"
    text += f"Daily summary: {'On' if user.daily_summary_enabled else 'Off'}\n"
    text += f"Timezone: {user.timezone}\n"
    text += f"Created: {user.created_at.strftime('%d/%m/%Y %I:%M %p')}"
    await update.message.reply_text(text)


async def recent_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    users = get_all_users(limit=20)
    if not users:
        await update.message.reply_text("No users found.")
        return

    lines = ["Recent users", ""]
    for user in users:
        lines.append(
            f"ID: {user.telegram_id} | @{user.username or 'N/A'} | premium: {'yes' if user.is_premium else 'no'} | blocked: {'yes' if user.is_blocked else 'no'}"
        )
    await update.message.reply_text("\n".join(lines))


async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_admin(update):
        return

    stats = get_dashboard_stats()
    text = "Master dashboard\n\n"
    text += f"Total users: {stats['total_users']}\n"
    text += f"Premium users: {stats['premium_users']}\n"
    text += f"Free users: {stats['free_users']}\n"
    text += f"Blocked users: {stats['blocked_users']}\n"
    text += f"Active reminders: {stats['active_reminders']}\n"
    text += f"Active habits: {stats['active_habits']}\n"
    text += f"Pending subscriptions: {stats['pending_subscriptions']}"
    await update.message.reply_text(text)


def run_admin():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30).build()
    app.add_handler(CommandHandler("admin", admin_start))
    app.add_handler(CommandHandler("pending", pending_subscriptions))
    app.add_handler(CommandHandler("approve", approve_sub))
    app.add_handler(CommandHandler("reject", reject_sub))
    app.add_handler(CommandHandler("dismisspremium", dismiss_premium_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("userinfo", user_info_command))
    app.add_handler(CommandHandler("recentusers", recent_users_command))
    app.add_handler(CommandHandler("users", user_stats))
    print("Admin panel is running...")
    try:
        app.run_polling(drop_pending_updates=True)
    except Conflict:
        print("Admin instance conflict: another process is already using this bot token. Stop the other process and run again.")


if __name__ == "__main__":
    run_admin()
