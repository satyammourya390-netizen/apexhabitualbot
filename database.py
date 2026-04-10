from datetime import datetime, timedelta

from config import FREE_LIMIT_HABITS, FREE_LIMIT_REMINDERS
from models import Habit, HabitLog, Reminder, SessionLocal, SubscriptionRequest, User, ensure_schema, init_db


def get_or_create_user(telegram_id, username=None, full_name=None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.username = username
            user.full_name = full_name
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


def get_user(telegram_id):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        db.close()


def get_all_users(limit=25):
    db = SessionLocal()
    try:
        return db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    finally:
        db.close()


def search_user(telegram_id):
    return get_user(telegram_id)


def block_user(telegram_id, reason=None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        user.is_blocked = True
        user.blocked_reason = reason
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def unblock_user(telegram_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        user.is_blocked = False
        user.blocked_reason = None
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def revoke_premium(telegram_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        user.is_premium = False
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def count_active_reminders(user_id):
    db = SessionLocal()
    try:
        return db.query(Reminder).filter(Reminder.user_id == user_id, Reminder.is_active.is_(True)).count()
    finally:
        db.close()


def count_active_habits(user_id):
    db = SessionLocal()
    try:
        return db.query(Habit).filter(Habit.user_id == user_id, Habit.is_active.is_(True)).count()
    finally:
        db.close()


def can_add_reminder(user_id):
    user = get_user(user_id)
    if user and user.is_premium:
        return True
    return count_active_reminders(user_id) < FREE_LIMIT_REMINDERS


def can_add_habit(user_id):
    user = get_user(user_id)
    if user and user.is_premium:
        return True
    return count_active_habits(user_id) < FREE_LIMIT_HABITS


def create_reminder(user_id, description, reminder_datetime, is_recurring=False, recurrence_type=None):
    if not can_add_reminder(user_id):
        return None
    db = SessionLocal()
    try:
        reminder = Reminder(
            user_id=user_id,
            description=description,
            reminder_datetime=reminder_datetime,
            is_recurring=is_recurring,
            recurrence_type=recurrence_type,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    finally:
        db.close()


def get_user_reminders(user_id, active_only=True):
    db = SessionLocal()
    try:
        query = db.query(Reminder).filter(Reminder.user_id == user_id)
        if active_only:
            query = query.filter(Reminder.is_active.is_(True))
        return query.order_by(Reminder.reminder_datetime.asc()).all()
    finally:
        db.close()


def get_due_reminders(current_time, grace_seconds=90):
    db = SessionLocal()
    try:
        start_time = current_time - timedelta(seconds=grace_seconds)
        reminders = (
            db.query(Reminder)
            .filter(
                Reminder.is_active.is_(True),
                Reminder.is_completed.is_(False),
                Reminder.reminder_datetime <= current_time,
                Reminder.reminder_datetime >= start_time,
            )
            .order_by(Reminder.reminder_datetime.asc())
            .all()
        )
        return reminders
    finally:
        db.close()


def complete_reminder(reminder_id):
    db = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.is_completed = True
            reminder.is_active = False
            db.commit()
            db.refresh(reminder)
        return reminder
    finally:
        db.close()


def mark_reminder_sent(reminder_id):
    db = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if not reminder:
            return None

        if reminder.is_recurring and reminder.recurrence_type in {"daily", "weekly"}:
            delta = timedelta(days=1) if reminder.recurrence_type == "daily" else timedelta(days=7)
            reminder.reminder_datetime = reminder.reminder_datetime + delta
            reminder.is_completed = False
            reminder.is_active = True
        else:
            reminder.is_completed = True
            reminder.is_active = False

        db.commit()
        db.refresh(reminder)
        return reminder
    finally:
        db.close()


def delete_reminder(reminder_id):
    db = SessionLocal()
    try:
        reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.is_active = False
            db.commit()
            db.refresh(reminder)
        return reminder
    finally:
        db.close()


def create_habit(user_id, description, frequency):
    if not can_add_habit(user_id):
        return None
    db = SessionLocal()
    try:
        habit = Habit(user_id=user_id, description=description, frequency=frequency)
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit
    finally:
        db.close()


def get_user_habits(user_id, active_only=True):
    db = SessionLocal()
    try:
        query = db.query(Habit).filter(Habit.user_id == user_id)
        if active_only:
            query = query.filter(Habit.is_active.is_(True))
        return query.order_by(Habit.created_at.asc()).all()
    finally:
        db.close()


def complete_habit(habit_id, user_id):
    db = SessionLocal()
    try:
        habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id, Habit.is_active.is_(True)).first()
        if not habit:
            return None

        now = datetime.utcnow()
        day_start = datetime.combine(now.date(), datetime.min.time())
        recent_log = (
            db.query(HabitLog)
            .filter(HabitLog.habit_id == habit_id, HabitLog.user_id == user_id, HabitLog.completed_at >= day_start)
            .first()
        )
        if recent_log:
            return habit

        last_log = (
            db.query(HabitLog)
            .filter(HabitLog.habit_id == habit_id, HabitLog.user_id == user_id)
            .order_by(HabitLog.completed_at.desc())
            .first()
        )

        log = HabitLog(habit_id=habit_id, user_id=user_id)
        db.add(log)

        if last_log:
            gap_days = (now.date() - last_log.completed_at.date()).days
            if habit.frequency == "daily":
                habit.current_streak = habit.current_streak + 1 if gap_days <= 1 else 1
            else:
                habit.current_streak = habit.current_streak + 1 if gap_days <= 7 else 1
        else:
            habit.current_streak = 1

        if habit.current_streak > habit.best_streak:
            habit.best_streak = habit.current_streak

        db.commit()
        db.refresh(habit)
        return habit
    finally:
        db.close()


def delete_habit(habit_id):
    db = SessionLocal()
    try:
        habit = db.query(Habit).filter(Habit.id == habit_id).first()
        if habit:
            habit.is_active = False
            db.commit()
            db.refresh(habit)
        return habit
    finally:
        db.close()


def get_habit_stats(habit_id):
    db = SessionLocal()
    try:
        habit = db.query(Habit).filter(Habit.id == habit_id).first()
        if not habit:
            return None
        total_logs = db.query(HabitLog).filter(HabitLog.habit_id == habit_id).count()
        return {
            "current_streak": habit.current_streak,
            "best_streak": habit.best_streak,
            "total_completions": total_logs,
        }
    finally:
        db.close()


def create_subscription_request(user_id, username, amount):
    db = SessionLocal()
    try:
        existing_request = (
            db.query(SubscriptionRequest)
            .filter(SubscriptionRequest.user_id == user_id, SubscriptionRequest.status == "pending")
            .first()
        )
        if existing_request:
            existing_request.amount = amount
            existing_request.username = username
            db.commit()
            db.refresh(existing_request)
            return existing_request

        request = SubscriptionRequest(user_id=user_id, username=username, amount=amount)
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
    finally:
        db.close()


def get_pending_subscriptions():
    db = SessionLocal()
    try:
        return (
            db.query(SubscriptionRequest)
            .filter(SubscriptionRequest.status == "pending")
            .order_by(SubscriptionRequest.created_at.desc())
            .all()
        )
    finally:
        db.close()


def approve_subscription(request_id):
    db = SessionLocal()
    try:
        request = db.query(SubscriptionRequest).filter(SubscriptionRequest.id == request_id).first()
        if not request:
            return None

        user = db.query(User).filter(User.telegram_id == request.user_id).first()
        if user:
            user.is_premium = True
        request.status = "approved"
        db.commit()
        db.refresh(request)
        return request
    finally:
        db.close()


def reject_subscription(request_id):
    db = SessionLocal()
    try:
        request = db.query(SubscriptionRequest).filter(SubscriptionRequest.id == request_id).first()
        if not request:
            return None
        request.status = "rejected"
        db.commit()
        db.refresh(request)
        return request
    finally:
        db.close()


def update_subscription_screenshot(request_id, screenshot_path):
    db = SessionLocal()
    try:
        request = db.query(SubscriptionRequest).filter(SubscriptionRequest.id == request_id).first()
        if request:
            request.screenshot_path = screenshot_path
            db.commit()
            db.refresh(request)
        return request
    finally:
        db.close()


def get_pending_subscription_by_user(user_id):
    db = SessionLocal()
    try:
        return (
            db.query(SubscriptionRequest)
            .filter(SubscriptionRequest.user_id == user_id, SubscriptionRequest.status == "pending")
            .order_by(SubscriptionRequest.created_at.desc())
            .first()
        )
    finally:
        db.close()


def get_dashboard_stats():
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        premium_users = db.query(User).filter(User.is_premium.is_(True)).count()
        blocked_users = db.query(User).filter(User.is_blocked.is_(True)).count()
        active_reminders = db.query(Reminder).filter(Reminder.is_active.is_(True)).count()
        active_habits = db.query(Habit).filter(Habit.is_active.is_(True)).count()
        pending_subscriptions = db.query(SubscriptionRequest).filter(SubscriptionRequest.status == "pending").count()
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "free_users": total_users - premium_users,
            "blocked_users": blocked_users,
            "active_reminders": active_reminders,
            "active_habits": active_habits,
            "pending_subscriptions": pending_subscriptions,
        }
    finally:
        db.close()


init_db()
ensure_schema()
