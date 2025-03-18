"""User repository"""

from typing import Optional
from sqlalchemy.orm import Session
from app.db.models import User, UserSettings


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, email: str, password_hash: str) -> User:
    """Create user"""
    db_user = User(username=username, email=email, password_hash=password_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create default settings for the user
    db_settings = UserSettings(user_id=db_user.id)
    db.add(db_settings)
    db.commit()

    return db_user


def update_user(
    db: Session,
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> Optional[User]:
    """Update user"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    if username is not None:
        db_user.username = username  # type: ignore
    if email is not None:
        db_user.email = email  # type: ignore
    if password_hash is not None:
        db_user.password_hash = password_hash  # type: ignore

    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_settings(db: Session, user_id: int) -> Optional[UserSettings]:
    """Get user settings"""
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()


def update_user_settings(
    db: Session, user_id: int, settings_data: dict
) -> Optional[UserSettings]:
    """Update user settings"""
    db_settings = get_user_settings(db, user_id)
    if not db_settings:
        return None

    for key, value in settings_data.items():
        if hasattr(db_settings, key):
            setattr(db_settings, key, value)

    db.commit()
    db.refresh(db_settings)
    return db_settings
