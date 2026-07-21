from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from pallisade_core.deals.models import Deal, DealTeamMember
from pallisade_core.deals.status import DealStatus, assert_transition_allowed
from pallisade_core.users.models import User


def _is_admin(user: User) -> bool:
    return user.role == "admin"


def create_deal(
    session: Session,
    *,
    lead: User,
    name: str,
    target_company: str,
    deal_type: str,
    sector: str | None = None,
    description: str | None = None,
    check_size_usd: int | None = None,
    expected_close_date=None,
) -> Deal:
    deal = Deal(
        name=name,
        target_company=target_company,
        deal_type=deal_type,
        sector=sector,
        description=description,
        check_size_usd=check_size_usd,
        expected_close_date=expected_close_date,
        deal_lead_id=lead.id,
        status=DealStatus.screening.value,
    )
    session.add(deal)
    return deal


def get_deal(session: Session, deal_id) -> Deal | None:
    return session.get(Deal, deal_id)


def can_view(session: Session, *, viewer: User, deal: Deal) -> bool:
    if deal.deleted_at is not None and not _is_admin(viewer):
        return False
    if _is_admin(viewer):
        return True
    if deal.deal_lead_id == viewer.id:
        return True
    member = session.execute(
        select(DealTeamMember).where(
            DealTeamMember.deal_id == deal.id, DealTeamMember.user_id == viewer.id
        )
    ).scalar_one_or_none()
    return member is not None


def list_visible(
    session: Session,
    *,
    viewer: User,
    status: str | None = None,
    q: str | None = None,
    include_deleted: bool = False,
) -> list[Deal]:
    stmt = select(Deal)
    if not include_deleted or not _is_admin(viewer):
        stmt = stmt.where(Deal.deleted_at.is_(None))
    if not _is_admin(viewer):
        is_lead = Deal.deal_lead_id == viewer.id
        is_member = exists().where(
            and_(DealTeamMember.deal_id == Deal.id, DealTeamMember.user_id == viewer.id)
        )
        stmt = stmt.where(or_(is_lead, is_member))
    if status:
        stmt = stmt.where(Deal.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Deal.name.ilike(like), Deal.target_company.ilike(like)))
    stmt = stmt.order_by(Deal.updated_at.desc())
    return list(session.execute(stmt).scalars().all())


def update_fields(session: Session, *, deal: Deal, **fields) -> Deal:
    for key, value in fields.items():
        if hasattr(deal, key) and key not in {"id", "deal_lead_id", "created_at", "deleted_at", "status"}:
            setattr(deal, key, value)
    session.add(deal)
    return deal


def transition_status(
    session: Session, *, deal: Deal, target: DealStatus, actor: User
) -> Deal:
    current = DealStatus(deal.status)
    assert_transition_allowed(current, target, is_admin=_is_admin(actor))
    deal.status = target.value
    session.add(deal)
    return deal


def soft_delete(session: Session, *, deal: Deal) -> None:
    deal.deleted_at = datetime.now(timezone.utc)
    session.add(deal)


def add_team_member(session: Session, *, deal: Deal, user: User) -> None:
    existing = session.execute(
        select(DealTeamMember).where(
            DealTeamMember.deal_id == deal.id, DealTeamMember.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(DealTeamMember(deal_id=deal.id, user_id=user.id))


def remove_team_member(session: Session, *, deal: Deal, user: User) -> None:
    existing = session.execute(
        select(DealTeamMember).where(
            DealTeamMember.deal_id == deal.id, DealTeamMember.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        session.delete(existing)


def list_team(session: Session, *, deal: Deal) -> list[User]:
    stmt = (
        select(User)
        .join(DealTeamMember, DealTeamMember.user_id == User.id)
        .where(DealTeamMember.deal_id == deal.id)
        .order_by(User.name)
    )
    return list(session.execute(stmt).scalars().all())
