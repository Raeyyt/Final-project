from fastapi import APIRouter, Depends, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from .. import schemas
from ..deps import get_current_user, get_db, require_roles
from ..models import Announcement, User, UserRole

router = APIRouter(prefix="/announcements", tags=["announcements"])


def _serialize(row: Announcement) -> schemas.AnnouncementRead:
    return schemas.AnnouncementRead(
        id=row.id,
        title=row.title,
        body=row.body,
        created_at=row.created_at,
        author_name=row.author.full_name,
    )


@router.get("/", response_model=list[schemas.AnnouncementRead])
def list_announcements(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(Announcement)
        .options(joinedload(Announcement.author))
        .order_by(desc(Announcement.created_at))
        .all()
    )
    return [_serialize(r) for r in rows]


@router.post(
    "/",
    response_model=schemas.AnnouncementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_announcement(
    data: schemas.AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    ann = Announcement(
        title=data.title.strip(),
        body=data.body.strip(),
        author_id=admin.id,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    ann = (
        db.query(Announcement)
        .options(joinedload(Announcement.author))
        .filter(Announcement.id == ann.id)
        .one()
    )
    return _serialize(ann)
