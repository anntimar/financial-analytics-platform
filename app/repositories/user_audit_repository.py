import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user_audit_event import UserAuditEvent


class UserAuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        actor_user_id: uuid.UUID | None,
        target_user_id: uuid.UUID,
        action: str,
        changes: dict[str, Any],
    ) -> UserAuditEvent:
        event = UserAuditEvent(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            changes=changes,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list(
        self,
        page: int,
        page_size: int,
        target_user_id: uuid.UUID | None,
        action: str | None,
    ) -> tuple[list[UserAuditEvent], int]:
        filters = []
        if target_user_id is not None:
            filters.append(UserAuditEvent.target_user_id == target_user_id)
        if action is not None:
            filters.append(UserAuditEvent.action == action)
        total = (
            self.session.scalar(select(func.count()).select_from(UserAuditEvent).where(*filters))
            or 0
        )
        statement = (
            select(UserAuditEvent)
            .where(*filters)
            .order_by(UserAuditEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total
