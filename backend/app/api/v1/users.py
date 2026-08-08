"""
User management endpoints.

Provides endpoints for user profile management and saved parcels.
Per blueprint: "The user's dashboard and profile page must be consolidated 
into a single unified page—do not split them into separate views."
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DatabaseSession
from app.models.parcel import SavedParcel
from app.schemas.user import UserResponse
from app.schemas.parcel import SavedParcelCreate, SavedParcelResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    """Get current user's profile information.
    
    Args:
        current_user: Authenticated user
    
    Returns:
        User profile data
    """
    return UserResponse.model_validate(current_user)


@router.get("/me/saved-parcels", response_model=list[SavedParcelResponse])
async def get_user_saved_parcels(current_user: CurrentUser, db: DatabaseSession):
    """Get current user's saved parcels.
    
    Per blueprint: "Saved parcels and searches reveal sensitive purchase intent. 
    User data must be strictly private with no public activity feeds."
    
    Args:
        current_user: Authenticated user
        db: Database session
    
    Returns:
        List of saved parcels with parcel data
    """
    result = await db.execute(
        select(SavedParcel)
        .where(SavedParcel.user_id == current_user.id)
        .options(selectinload(SavedParcel.parcel))
        .order_by(SavedParcel.saved_at.desc())
    )
    saved_parcels = result.scalars().all()
    
    return [SavedParcelResponse.model_validate(sp) for sp in saved_parcels]


@router.post("/me/saved-parcels", response_model=SavedParcelResponse, status_code=status.HTTP_201_CREATED)
async def save_parcel(
    data: SavedParcelCreate,
    current_user: CurrentUser,
    db: DatabaseSession
):
    """Save a parcel to user's collection.
    
    Privacy note: Saved parcels are private to the user only.
    
    Args:
        data: Parcel save request
        current_user: Authenticated user
        db: Database session
    
    Returns:
        Saved parcel data
    
    Raises:
        HTTPException: If parcel already saved or not found
    """
    # Check if already saved
    result = await db.execute(
        select(SavedParcel).where(
            SavedParcel.user_id == current_user.id,
            SavedParcel.parcel_id == data.parcel_id,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parcel already saved",
        )
    
    # Create saved parcel
    saved_parcel = SavedParcel(
        user_id=current_user.id,
        parcel_id=data.parcel_id,
        notes=data.notes,
    )
    
    db.add(saved_parcel)
    await db.commit()
    await db.refresh(saved_parcel, ["parcel"])
    
    return SavedParcelResponse.model_validate(saved_parcel)


@router.delete("/me/saved-parcels/{saved_parcel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_saved_parcel(
    saved_parcel_id: int,
    current_user: CurrentUser,
    db: DatabaseSession
):
    """Remove a parcel from user's saved collection.
    
    Args:
        saved_parcel_id: ID of saved parcel to remove
        current_user: Authenticated user
        db: Database session
    
    Raises:
        HTTPException: If saved parcel not found or not owned by user
    """
    result = await db.execute(
        select(SavedParcel).where(
            SavedParcel.id == saved_parcel_id,
            SavedParcel.user_id == current_user.id,
        )
    )
    saved_parcel = result.scalar_one_or_none()
    
    if not saved_parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved parcel not found",
        )
    
    await db.delete(saved_parcel)
    await db.commit()
