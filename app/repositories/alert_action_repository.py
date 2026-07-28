import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_action import AlertAction
from app.schemas.alert import AlertWorkflowStatus


class AlertActionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_period(
        self, company_id: uuid.UUID, start_date: date, end_date: date
    ) -> list[AlertAction]:
        statement = select(AlertAction).where(
            AlertAction.company_id == company_id,
            AlertAction.reference_date >= start_date,
            AlertAction.reference_date <= end_date,
        )
        return list(self.session.scalars(statement))

    def get(
        self, company_id: uuid.UUID, alert_code: str, reference_date: date
    ) -> AlertAction | None:
        return self.session.scalar(
            select(AlertAction).where(
                AlertAction.company_id == company_id,
                AlertAction.alert_code == alert_code,
                AlertAction.reference_date == reference_date,
            )
        )

    def save(
        self,
        action: AlertAction | None,
        company_id: uuid.UUID,
        alert_code: str,
        reference_date: date,
        status: AlertWorkflowStatus,
        note: str | None,
        user_id: uuid.UUID,
    ) -> AlertAction:
        if action is None:
            action = AlertAction(
                company_id=company_id,
                alert_code=alert_code,
                reference_date=reference_date,
                status=status,
                note=note,
                updated_by=user_id,
            )
            self.session.add(action)
        else:
            action.status = status
            action.note = note
            action.updated_by = user_id
        self.session.commit()
        self.session.refresh(action)
        return action
