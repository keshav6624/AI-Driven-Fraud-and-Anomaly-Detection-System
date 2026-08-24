"""Investigation case service — CRUD for cases and notes."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.app.models.orm import (
    InvestigationCase,
    CaseNote,
    Member,
    State,
    Constituency,
)
from backend.app.schemas.investigation import (
    InvestigationCaseCreate,
    InvestigationCaseUpdate,
    CaseNoteCreate,
    InvestigationCaseResponse,
    InvestigationCaseListResponse,
    CaseNoteResponse,
)


def _enrich_case(case: InvestigationCase) -> InvestigationCaseResponse:
    member = case._member if hasattr(case, "_member") else None
    return InvestigationCaseResponse(
        case_id=case.case_id,
        member_id=case.member_id,
        mp_name=member.mp_name if member else None,
        state=member.state_rel.name if member and hasattr(member, "state_rel") else None,
        constituency=member.constituency_rel.name if member and hasattr(member, "constituency_rel") else None,
        title=case.title,
        description=case.description,
        status=case.status,
        priority=case.priority,
        created_by=case.created_by,
        assigned_to=case.assigned_to,
        resolution_notes=case.resolution_notes,
        created_at=case.created_at,
        updated_at=case.updated_at,
        notes=[
            CaseNoteResponse(
                note_id=n.note_id, case_id=n.case_id, author_id=n.author_id,
                body=n.body, created_at=n.created_at,
            )
            for n in case.notes
        ],
    )


def create_case(db: Session, data: InvestigationCaseCreate, user_id: int) -> InvestigationCaseResponse:
    case = InvestigationCase(
        member_id=data.member_id,
        title=data.title,
        description=data.description,
        status="OPEN",
        priority=data.priority,
        created_by=user_id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    member = db.query(Member).filter(Member.member_id == data.member_id).first()
    case._member = member
    return _enrich_case(case)


def get_case(db: Session, case_id: int) -> InvestigationCaseResponse | None:
    case = (
        db.query(InvestigationCase)
        .options(joinedload(InvestigationCase.notes))
        .filter(InvestigationCase.case_id == case_id)
        .first()
    )
    if not case:
        return None
    member = db.query(Member).filter(Member.member_id == case.member_id).first()
    case._member = member
    return _enrich_case(case)


def list_cases(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    member_id: Optional[int] = None,
) -> InvestigationCaseListResponse:
    q = db.query(InvestigationCase).options(joinedload(InvestigationCase.notes))
    if status:
        q = q.filter(InvestigationCase.status == status)
    if priority:
        q = q.filter(InvestigationCase.priority == priority)
    if member_id:
        q = q.filter(InvestigationCase.member_id == member_id)
    total = q.count()
    cases = q.order_by(InvestigationCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for c in cases:
        member = db.query(Member).filter(Member.member_id == c.member_id).first()
        c._member = member
        items.append(_enrich_case(c))
    return InvestigationCaseListResponse(items=items, total=total, page=page, page_size=page_size)


def update_case(db: Session, case_id: int, data: InvestigationCaseUpdate) -> InvestigationCaseResponse | None:
    case = db.query(InvestigationCase).options(joinedload(InvestigationCase.notes)).filter(InvestigationCase.case_id == case_id).first()
    if not case:
        return None
    if data.status is not None:
        case.status = data.status
    if data.priority is not None:
        case.priority = data.priority
    if data.assigned_to is not None:
        case.assigned_to = data.assigned_to
    if data.resolution_notes is not None:
        case.resolution_notes = data.resolution_notes
    db.commit()
    db.refresh(case)
    member = db.query(Member).filter(Member.member_id == case.member_id).first()
    case._member = member
    return _enrich_case(case)


def add_note(db: Session, case_id: int, data: CaseNoteCreate, user_id: int) -> CaseNoteResponse:
    note = CaseNote(case_id=case_id, author_id=user_id, body=data.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return CaseNoteResponse(
        note_id=note.note_id, case_id=note.case_id, author_id=note.author_id,
        body=note.body, created_at=note.created_at,
    )
