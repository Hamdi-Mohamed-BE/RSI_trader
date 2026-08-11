from typing import Any

from sqlalchemy.orm import Session

from ..domain.enums import AuditSeverity
from ..models import AuditEvent


def record_audit(
    session: Session,
    *,
    action: str,
    message: str,
    actor: str = "system",
    target_type: str = "system",
    target_id: str = "",
    severity: AuditSeverity = AuditSeverity.INFO,
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        message=message,
        target_type=target_type,
        target_id=target_id,
        severity=severity.value,
        details=details or {},
        ip_address=ip_address,
    )
    session.add(event)
    return event
