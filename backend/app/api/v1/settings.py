"""
User Settings API endpoints.

Handles user preferences like LLM provider selection.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserSettings, UserSettingsUpdate

router = APIRouter()


@router.get("/", response_model=UserSettings)
def get_settings(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user settings.

    Returns:
        UserSettings with llm_provider preference
    """
    return UserSettings(
        llm_provider=current_user.llm_provider or "auto",
    )


@router.put("/", response_model=UserSettings)
def update_settings(
    data: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user settings.

    Args:
        data: Settings to update (llm_provider)

    Returns:
        Updated UserSettings
    """
    current_user.llm_provider = data.llm_provider
    db.commit()
    db.refresh(current_user)

    return UserSettings(
        llm_provider=current_user.llm_provider,
    )


@router.get("/llm/status")
def get_llm_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get LLM provider status for the current user.

    Shows which provider is active, available fallbacks, and models.

    Returns:
        Dict with provider status info
    """
    from app.services.llm_client import LLMClient

    provider = current_user.llm_provider or "auto"
    llm = LLMClient(provider=None if provider == "auto" else provider)
    status = llm.get_provider_status()
    status["user_preference"] = provider

    return status
