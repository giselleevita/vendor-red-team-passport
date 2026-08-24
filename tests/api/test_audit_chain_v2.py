from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from apps.api.config import get_settings
from apps.api.services import audit
from scripts.verify_audit_log import verify_audit_log


@pytest.fixture
def audit_log(monkeypatch, tmp_path):
    path = tmp_path / "events.log"
    monkeypatch.setenv("VENDOR_RTP_MANIFEST_HMAC_KEY", "chain-secret")
    monkeypatch.setattr(audit, "_audit_log_path", lambda: path)
    get_settings.cache_clear()
    for index in range(4):
        audit.log_audit_event(
            action="test",
            result="allow",
            actor="actor",
            tenant_id="tenant",
            resource=f"/events/{index}",
        )
    return path


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_chain_verifies_and_detects_modification(audit_log) -> None:
    assert verify_audit_log(audit_log, "chain-secret")
    events = [json.loads(line) for line in _lines(audit_log)]
    events[1]["resource"] = "/modified"
    audit_log.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    assert not verify_audit_log(audit_log, "chain-secret")


@pytest.mark.parametrize("mutation", ["delete", "insert", "reorder", "truncate_tail"])
def test_chain_detects_structural_mutations(audit_log, mutation: str) -> None:
    lines = _lines(audit_log)
    if mutation == "delete":
        del lines[1]
    elif mutation == "insert":
        lines.insert(2, lines[0])
    elif mutation == "reorder":
        lines[1], lines[2] = lines[2], lines[1]
    else:
        lines.pop()
    audit_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not verify_audit_log(audit_log, "chain-secret")


def test_concurrent_writers_receive_unique_contiguous_sequences(monkeypatch, tmp_path) -> None:
    path = tmp_path / "events.log"
    monkeypatch.setenv("VENDOR_RTP_MANIFEST_HMAC_KEY", "chain-secret")
    monkeypatch.setattr(audit, "_audit_log_path", lambda: path)
    get_settings.cache_clear()

    def write(index: int) -> None:
        audit.log_audit_event(
            action="concurrent",
            result="allow",
            actor="actor",
            tenant_id="tenant",
            resource=f"/{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(30)))
    events = [json.loads(line) for line in _lines(path)]
    assert [event["sequence"] for event in events] == list(range(1, 31))
    assert verify_audit_log(path, "chain-secret")
