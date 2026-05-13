from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..database import engine
from ..deps import get_db, get_current_user
from ..models import User, UserRole
from ..security import get_password_hash

router = APIRouter(prefix="/accountants", tags=["accountants"])

@router.get("/", response_model=List[schemas.UserRead])
def get_accountants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    accountants = db.query(User).filter(User.role == UserRole.ACCOUNTANT).all()
    return accountants

@router.post("/", response_model=schemas.UserRead)
def create_accountant(
    accountant_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Force role to ACCOUNTANT if not set or incorrect
    if accountant_in.role != UserRole.ACCOUNTANT:
         raise HTTPException(status_code=400, detail="Can only create accountants here")

    existing_user = db.query(User).filter(User.username == accountant_in.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(accountant_in.password)
    new_accountant = User(
        username=accountant_in.username,
        full_name=accountant_in.full_name,
        hashed_password=hashed_password,
        role=UserRole.ACCOUNTANT,
    )
    db.add(new_accountant)
    db.commit()
    db.refresh(new_accountant)
    return new_accountant

@router.delete("/{accountant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accountant(
    accountant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    accountant = db.get(User, accountant_id)
    if not accountant:
        raise HTTPException(status_code=404, detail="Accountant not found")
    
    if accountant.role != UserRole.ACCOUNTANT:
        raise HTTPException(status_code=400, detail="User is not an accountant")

    db.delete(accountant)
    db.commit()
    return None
