"""User routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.auth import get_current_user, get_password_hash
from app.schemas.users import User, UserUpdate
from app.schemas.settings import UserSettings, UserSettingsUpdate
from app.db.repositories import users as users_repository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/settings", response_model=UserSettings)
def read_user_settings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get user settings"""
    settings = users_repository.get_user_settings(db, current_user.id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found"
        )
    return settings


@router.put("/me/settings", response_model=UserSettings)
def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user settings"""
    settings = users_repository.update_user_settings(
        db, current_user.id, settings_update.model_dump(exclude_unset=True)
    )
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found"
        )
    return settings


@router.put("/me", response_model=User)
def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user"""
    # Check if username is being updated and is already taken
    if user_update.username and user_update.username != current_user.username:
        db_user = users_repository.get_user_by_username(db, user_update.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

    # Check if email is being updated and is already taken
    if user_update.email and user_update.email != current_user.email:
        db_user = users_repository.get_user_by_email(db, user_update.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Prepare update data
    update_data = {}
    if user_update.username:
        update_data["username"] = user_update.username
    if user_update.email:
        update_data["email"] = user_update.email
    if user_update.password:
        update_data["password_hash"] = get_password_hash(user_update.password)

    # Update user
    updated_user = users_repository.update_user(db, current_user.id, **update_data)

    return updated_user
