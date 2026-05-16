import logging
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .. import schemas
from ..models import UserRole
from ..security import verify_password, create_access_token, get_password_hash
from ..deps import get_db, get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: sqlite3.Connection = Depends(get_db),
):
    logger.info("Login attempt for username='%s'", form_data.username)
    
    user = db.execute("SELECT * FROM users WHERE username = ?", (form_data.username,)).fetchone()
    
    if user:
        user = dict(user)
        logger.info("User '%s' found with role %s", user["username"], user["role"])
    else:
        logger.warning("User '%s' not found in DB", form_data.username)
        
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(
        {"sub": user["username"], "role": user["role"]}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=list[schemas.UserRead])
def get_all_users(
    db: sqlite3.Connection = Depends(get_db),
    _: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR))
):
    users = db.execute("SELECT * FROM users").fetchall()
    return [dict(u) for u in users]

@router.patch("/me", response_model=dict)
def update_current_user(
    update_data: schemas.UserUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not verify_password(update_data.old_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    if update_data.username:
        existing = db.execute("SELECT id FROM users WHERE username = ?", (update_data.username,)).fetchone()
        if existing and existing["id"] != current_user["id"]:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user["username"] = update_data.username
        
    if update_data.new_password:
        current_user["hashed_password"] = get_password_hash(update_data.new_password)
        
    db.execute(
        "UPDATE users SET username = ?, hashed_password = ? WHERE id = ?",
        (current_user["username"], current_user["hashed_password"], current_user["id"])
    )
    db.commit()
    
    new_token = create_access_token({"sub": current_user["username"], "role": current_user["role"]})
    return {"access_token": new_token, "user": current_user}

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: schemas.UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    existing_username = db.execute("SELECT id FROM users WHERE username = ?", (user_in.username,)).fetchone()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    existing_name = db.execute(
        "SELECT id FROM users WHERE lower(full_name) = ? AND role = ?", 
        (user_in.full_name.lower(), user_in.role.value)
    ).fetchone()
    if existing_name:
        raise HTTPException(status_code=400, detail=f"A user with the name '{user_in.full_name}' is already registered as a {user_in.role.value}")
    
    hashed_pw = get_password_hash(user_in.password)
    
    cursor = db.execute(
        "INSERT INTO users (username, full_name, hashed_password, role, teaching_title) VALUES (?, ?, ?, ?, ?)",
        (user_in.username, user_in.full_name, hashed_pw, user_in.role.value, user_in.teaching_title)
    )
    db.commit()
    
    new_user = db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(new_user)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    user = db.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["id"] == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own active session")
        
    if user["role"] == UserRole.TEACHER.value:
        db.execute("UPDATE classes SET teacher_id = NULL WHERE teacher_id = ?", (user["id"],))
        db.execute("UPDATE students SET teacher_id = NULL WHERE teacher_id = ?", (user["id"],))
            
    if user["role"] == UserRole.PARENT.value:
        db.execute("UPDATE students SET parent_id = NULL WHERE parent_id = ?", (user["id"],))
            
    db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    db.commit()
    return None
