from __future__ import annotations

from pallisade_core.deals.models import Deal
from pallisade_core.users.models import User


class PermissionDenied(Exception):
    pass


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise PermissionDenied("admin role required")


def can_manage_deal(*, actor: User, deal: Deal) -> bool:
    return actor.role == "admin" or deal.deal_lead_id == actor.id
