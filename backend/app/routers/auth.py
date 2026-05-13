import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import schemas
from ..database import engine
from ..models import User, UserRole
from ..security import verify_password, create_access_token
from ..deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)
logger.info("Auth router using DB url: %s", engine.url)


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    logger.info("Login attempt for username='%s'", form_data.username)
    user: User | None = (
        db.query(User).filter(User.username == form_data.username).first()
    )
    if user:
        logger.info("User '%s' found with role %s", user.username, user.role)
    else:
        logger.warning("User '%s' not found in DB", form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(
        {"sub": user.username, "role": user.role}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=list[schemas.UserRead])
def get_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR))
):
    return db.query(User).all()

@router.patch("/me", response_model=dict)
def update_current_user(
    update_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..security import verify_password, get_password_hash, create_access_token
    if not verify_password(update_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    if update_data.username:
        existing = db.query(User).filter(User.username == update_data.username).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = update_data.username
        
    if update_data.new_password:
        current_user.hashed_password = get_password_hash(update_data.new_password)
        
    db.commit()
    db.refresh(current_user)
    
    new_token = create_access_token({"sub": current_user.username, "role": current_user.role})
    return {"access_token": new_token, "user": schemas.UserRead.model_validate(current_user).model_dump()}

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    from ..security import get_password_hash
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
        
    if db.query(User).filter(func.lower(User.full_name) == user_in.full_name.lower(), User.role == user_in.role).first():
        raise HTTPException(status_code=400, detail=f"A user with the name '{user_in.full_name}' is already registered as a {user_in.role.value}")
    
    new_user = User(
        username=user_in.username,
        full_name=user_in.full_name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
        teaching_title=user_in.teaching_title,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own active session")
        
    from ..models import Student, ClassRoom
    if user.role == UserRole.TEACHER:
        db.query(ClassRoom).filter(ClassRoom.teacher_id == user.id).update({ClassRoom.teacher_id: None})
        db.query(Student).filter(Student.teacher_id == user.id).update({Student.teacher_id: None})
            
    if user.role == UserRole.PARENT:
        db.query(Student).filter(Student.parent_id == user.id).update({Student.parent_id: None})
            
    db.delete(user)
    db.commit()
    return None

