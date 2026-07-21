from __future__ import annotations

import pytest

from pallisade_core.deals.status import (
    DealStatus, IllegalStatusTransition, assert_transition_allowed,
)


def test_allowed_transitions():
    assert_transition_allowed(DealStatus.screening, DealStatus.loi, is_admin=False)
    assert_transition_allowed(DealStatus.loi, DealStatus.dd, is_admin=False)
    assert_transition_allowed(DealStatus.dd, DealStatus.ic, is_admin=False)
    assert_transition_allowed(DealStatus.ic, DealStatus.closed_won, is_admin=False)
    assert_transition_allowed(DealStatus.screening, DealStatus.closed_lost, is_admin=False)


@pytest.mark.parametrize("from_,to_", [
    (DealStatus.screening, DealStatus.dd),
    (DealStatus.loi, DealStatus.ic),
    (DealStatus.closed_won, DealStatus.screening),
    (DealStatus.dd, DealStatus.screening),
])
def test_illegal_for_member(from_, to_):
    with pytest.raises(IllegalStatusTransition):
        assert_transition_allowed(from_, to_, is_admin=False)


def test_admin_can_override():
    assert_transition_allowed(DealStatus.closed_won, DealStatus.dd, is_admin=True)
