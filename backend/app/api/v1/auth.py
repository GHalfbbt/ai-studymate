"""
Authentication API endpoints.

Provides user registration, login, and profile retrieval.
Uses JWT tokens for stateless authentication.

Two login endpoints are provided:
- POST /login       — JSON body (used by the frontend SPA)
- POST /token       — OAuth2 form (used by Swagger "Authorize" button)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Creates the user and a default workspace.
    Returns the user profile (without token — user must login after).
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user with hashed password
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.flush()  # Get the user ID without committing

    # Create a default workspace for the new user
    default_workspace = Workspace(
        name="My Workspace",
        description="Default workspace",
        user_id=user.id,
    )
    db.add(default_workspace)
    db.commit()
    db.refresh(user)

    print(f"✅ Nuevo usuario registrado: {user.email}")
    return user


# ─── Internal helper ────────────────────────────────────

def _authenticate_user(email: str, password: str, db: Session) -> Token:
    """
    Shared authentication logic for both login endpoints.

    Raises HTTPException 401 if credentials are invalid.
    Returns a Token on success.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    print(f"🔐 Login exitoso: {user.email}")
    return Token(access_token=access_token, token_type="bearer")


# ─── JSON login (frontend SPA) ─────────────────────────

@router.post(
    "/login",
    response_model=Token,
    summary="Login with JSON body (frontend)",
)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user with JSON body and return JWT access token.

    Expected body: { "email": "...", "password": "..." }

    The token should be included in subsequent requests as:
    Authorization: Bearer <token>
    """
    return _authenticate_user(credentials.email, credentials.password, db)


# ─── OAuth2 form login (Swagger UI) ────────────────────

@router.post(
    "/token",
    response_model=Token,
    summary="Login with OAuth2 form (Swagger)",
)
async def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible token endpoint for Swagger UI "Authorize" button.

    Accepts application/x-www-form-urlencoded with:
    - username (email)
    - password
    """
    return _authenticate_user(form_data.username, form_data.password, db)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the profile of the currently authenticated user.

    Requires a valid JWT token in the Authorization header.
    """
    return current_user
