from pallisade_core.errors import HardError


def test_hard_error_is_an_exception():
    exc = HardError("boom")
    assert isinstance(exc, Exception)
    assert str(exc) == "boom"


def test_hard_error_subclass_is_recognised():
    class InvalidParams(HardError):
        pass

    exc = InvalidParams("bad")
    assert isinstance(exc, HardError)
    assert isinstance(exc, Exception)
