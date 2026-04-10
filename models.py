from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def ensure_schema():
    with engine.begin() as connection:
        user_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if "is_blocked" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0")
        if "blocked_reason" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN blocked_reason VARCHAR")
        if "reminders_enabled" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN reminders_enabled BOOLEAN DEFAULT 1")
        if "daily_summary_enabled" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN daily_summary_enabled BOOLEAN DEFAULT 1")
        if "timezone" not in user_columns:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN timezone VARCHAR DEFAULT 'Asia/Kolkata'")


def utc_now():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    blocked_reason = Column(String, nullable=True)
    reminders_enabled = Column(Boolean, default=True)
    daily_summary_enabled = Column(Boolean, default=True)
    timezone = Column(String, default="Asia/Kolkata")
    created_at = Column(DateTime, default=utc_now)

    reminders = relationship("Reminder", back_populates="user")
    habits = relationship("Habit", back_populates="user")
    habit_logs = relationship("HabitLog", back_populates="user")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    description = Column(Text, nullable=False)
    reminder_datetime = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_type = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="reminders")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    description = Column(Text, nullable=False)
    frequency = Column(String, nullable=False)
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="habits")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    completed_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="habit_logs")
    habit = relationship("Habit")


class SubscriptionRequest(Base):
    __tablename__ = "subscription_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String, nullable=True)
    amount = Column(Integer, nullable=False)
    screenshot_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=utc_now)
