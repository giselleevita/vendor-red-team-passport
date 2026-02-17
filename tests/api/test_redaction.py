from apps.api.services.redaction import sanitize_text


def test_redaction_codeblock() -> None:
    assert sanitize_text("```\\nsecret\\n```") == "<redacted: code-block output>"


def test_redaction_secret_like() -> None:
    assert sanitize_text("JWT_SECRET=abc") == "<redacted: secret-like content>"


def test_redaction_length_cap() -> None:
    out = sanitize_text("x" * 1000, limit=10)
    assert out == "x" * 10

