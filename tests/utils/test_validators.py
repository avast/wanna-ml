import pytest

from wanna.core.utils.validators import validate_only_one_must_be_set

def test_validate_only_one_must_be_set_raises_error_when_none_set():
    with pytest.raises(ValueError, match="One of .* must be set."):
        validate_only_one_must_be_set(None, {"a": None, "b": None})

def test_validate_only_one_must_be_set_raises_error_when_more_than_one_set():
    with pytest.raises(ValueError, match="Specify only one of .*"):
        validate_only_one_must_be_set(None, {"a": 1, "b": 2})

def test_validate_only_one_must_be_set_returns_value_when_one_set():
    result = validate_only_one_must_be_set(None, {"a": 1, "b": None})
    assert result == {"a": 1, "b": None}
