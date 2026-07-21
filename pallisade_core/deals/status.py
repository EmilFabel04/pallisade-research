from __future__ import annotations

from enum import Enum


class DealStatus(str, Enum):
    screening = "screening"
    loi = "loi"
    dd = "dd"
    ic = "ic"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


ALLOWED_TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
    DealStatus.screening: {DealStatus.loi, DealStatus.closed_lost},
    DealStatus.loi: {DealStatus.dd, DealStatus.closed_lost},
    DealStatus.dd: {DealStatus.ic, DealStatus.closed_lost},
    DealStatus.ic: {DealStatus.closed_won, DealStatus.closed_lost},
    DealStatus.closed_won: set(),
    DealStatus.closed_lost: set(),
}


class IllegalStatusTransition(ValueError):
    pass


def assert_transition_allowed(
    current: DealStatus, target: DealStatus, *, is_admin: bool
) -> None:
    if current == target:
        return
    if is_admin:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise IllegalStatusTransition(f"{current.value} -> {target.value} not allowed")
