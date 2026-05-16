import sqlite3
from fastapi import APIRouter, Depends, status
from typing import List

from .. import schemas
from ..deps import get_current_user, get_db, require_roles
from ..models import UserRole

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/", response_model=list[schemas.AnnouncementRead])
def list_announcements(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = """
        SELECT a.id, a.title, a.body, a.created_at, a.target_class_id, u.full_name as author_name, c.name as target_class_name
        FROM announcements a
        JOIN users u ON a.author_id = u.id
        LEFT JOIN classes c ON a.target_class_id = c.id
    """
    params = []
    
    if current_user["role"] == UserRole.PARENT.value:
        query += """
        WHERE a.target_class_id IS NULL OR a.target_class_id IN (
            SELECT class_id FROM students WHERE parent_id = ? AND is_active = 1
        )
        """
        params.append(current_user["id"])
        
    query += " ORDER BY a.created_at DESC"
    
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.post(
    "/",
    response_model=schemas.AnnouncementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_announcement(
    data: schemas.AnnouncementCreate,
    db: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles(UserRole.ADMIN, UserRole.DIRECTOR)),
):
    cursor = db.execute(
        "INSERT INTO announcements (title, body, author_id, target_class_id) VALUES (?, ?, ?, ?)",
        (data.title.strip(), data.body.strip(), admin["id"], data.target_class_id)
    )
    db.commit()
    
    query = """
        SELECT a.id, a.title, a.body, a.created_at, a.target_class_id, u.full_name as author_name, c.name as target_class_name
        FROM announcements a
        JOIN users u ON a.author_id = u.id
        LEFT JOIN classes c ON a.target_class_id = c.id
        WHERE a.id = ?
    """
    row = db.execute(query, (cursor.lastrowid,)).fetchone()
    return dict(row)
