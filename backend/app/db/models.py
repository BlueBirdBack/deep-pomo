from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tasks = relationship("Task", back_populates="user")
    pomodoro_sessions = relationship("PomodoroSession", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(
        String(20), CheckConstraint("priority IN ('high', 'medium', 'low')")
    )
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'blocked')"),
        default="pending",
    )
    parent_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))
    path = Column(String, index=True)  # PostgreSQL LTREE type
    color_code = Column(String(9))
    estimated_duration = Column(Integer)  # in seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="tasks")
    children = relationship(
        "Task",
        backref=relationship("Task", remote_side=[id]),
        cascade="all, delete-orphan",
    )
    pomodoro_associations = relationship(
        "PomodoroTaskAssociation", back_populates="task"
    )
    history = relationship("TaskHistory", back_populates="task")

    __table_args__ = (CheckConstraint("parent_id != id", name="valid_parent"),)


class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration = Column(Integer, nullable=False)  # Planned duration in seconds
    actual_duration = Column(Integer)  # Actual duration in seconds
    session_type = Column(
        String(20),
        CheckConstraint("session_type IN ('work', 'short_break', 'long_break')"),
        nullable=False,
    )
    completed = Column(Boolean, default=False)
    interruption_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="pomodoro_sessions")
    task_associations = relationship(
        "PomodoroTaskAssociation", back_populates="pomodoro_session"
    )

    __table_args__ = (
        CheckConstraint(
            "end_time IS NULL OR end_time > start_time", name="valid_time_range"
        ),
    )


class PomodoroTaskAssociation(Base):
    __tablename__ = "pomodoro_task_associations"

    id = Column(Integer, primary_key=True, index=True)
    pomodoro_session_id = Column(
        Integer, ForeignKey("pomodoro_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    time_spent = Column(Integer)  # Time spent on this task (seconds)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True))

    pomodoro_session = relationship(
        "PomodoroSession", back_populates="task_associations"
    )
    task = relationship("Task", back_populates="pomodoro_associations")


class TaskHistory(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action = Column(String(20), nullable=False)  # Enum in PostgreSQL
    changes = Column(JSONB, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="history")
    user = relationship("User")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    pomodoro_duration = Column(Integer, default=1500)  # 25 minutes in seconds
    short_break_duration = Column(Integer, default=300)  # 5 minutes
    long_break_duration = Column(Integer, default=900)  # 15 minutes
    pomodoros_until_long_break = Column(Integer, default=4)
    theme = Column(String(20), default="light")
    notification_enabled = Column(Boolean, default=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="settings")
