from api.utils.security import validate_password_strength, sanitize_input


def test_validate_password_strength_accepts_strong_password():
    result = validate_password_strength("StrongPass123!")
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_password_strength_rejects_weak_password():
    result = validate_password_strength("weak")
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_sanitize_input_removes_unsafe_chars():
    raw_value = "  test<script>alert(1)</script>@mail.com  "
    sanitized = sanitize_input(raw_value)
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert sanitized.startswith("testscript")
