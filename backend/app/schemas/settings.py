"""Settings schemas"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserSettingsBase(BaseModel):
    """Base user settings model"""

    pomodoro_duration: int = 1500  # 25 minutes in seconds
    short_break_duration: int = 300  # 5 minutes
    long_break_duration: int = 900  # 15 minutes
    pomodoros_until_long_break: int = 4
    theme: str = "light"
    notification_enabled: bool = True


class UserSettingsUpdate(BaseModel):
    """User settings update model"""

    pomodoro_duration: Optional[int] = None
    short_break_duration: Optional[int] = None
    long_break_duration: Optional[int] = None
    pomodoros_until_long_break: Optional[int] = None
    theme: Optional[str] = None
    notification_enabled: Optional[bool] = None


class UserSettings(UserSettingsBase):
    """User settings model"""

    user_id: int
    updated_at: datetime

    # Replace the class Config with this:
    model_config = ConfigDict(from_attributes=True)
