from __future__ import annotations

import re


_RE_SECRET = re.compile(
    r"(?i)(api[_-]?key|jwt[_-]?secret|password\\s*=|token\\s*=|bearer\\s+|-----begin|ssh-rsa)",
)
_RE_CODEBLOCK = re.compile(r"```.*?```", flags=re.DOTALL)


def sanitize_text(text: str, limit: int = 180) -> str:
    """
    Sanitizes model output for safe persistence:
    - redacts code blocks
    - redacts secret-like patterns
    - caps length
    """
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if _RE_CODEBLOCK.search(t):
        return "<redacted: code-block output>"
    if _RE_SECRET.search(t):
        return "<redacted: secret-like content>"
    t = t.replace("\n", " ")
    return t[:limit]

