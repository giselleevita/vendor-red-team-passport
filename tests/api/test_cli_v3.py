from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

from apps.api import cli


def test_parser_exposes_all_packaged_commands() -> None:
    parser = cli._parser()
    assert parser.parse_args(["run", "--model", "target"]).command == "run"
    assert parser.parse_args(["benchmark", "--models", "a", "b"]).models == ["a", "b"]
    assert parser.parse_args(["verify-manifest", "--run-id", "run-1"]).run_id == "run-1"
    parsed_audit = parser.parse_args(["verify-audit", "--secret", "fixture-value"])
    assert vars(parsed_audit)["secret"] == "fixture-value"  # noqa: S105 -- CLI fixture


def test_run_command_resolves_profile_and_prints_location(monkeypatch, capsys, tmp_path) -> None:
    profile = {"model": "profile-model", "only_classes": ["A4"], "a9_mode": "strict", "params": {}}
    monkeypatch.setattr(cli, "load_profile", lambda _name: profile)
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(default_model="default"))
    captured = {}

    def run_orchestrated(**kwargs):
        captured.update(kwargs)
        return "run-1"

    monkeypatch.setattr(cli, "run_orchestrated", run_orchestrated)
    monkeypatch.setattr(cli, "run_dir", lambda _run_id: tmp_path)
    args = argparse.Namespace(
        profile="quick", model="", suite="", base_url="", only_classes=[], a9_mode="", run_id=""
    )
    assert cli._run(args) == 0
    assert captured["a9_mode"] == "strict"
    assert json.loads(capsys.readouterr().out)["run_id"] == "run-1"


def test_benchmark_writes_summaries(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "run_orchestrated", lambda model, **_kwargs: f"run-{model}")
    summary = SimpleNamespace(model_dump=lambda: {"release_gate": "PASS"})
    monkeypatch.setattr(cli, "load_passport", lambda _run_id: SimpleNamespace(summary=summary))
    output = tmp_path / "benchmark.json"
    args = argparse.Namespace(models=["a", "b"], profile="", suite="suite.json", only_classes=[], out=str(output))
    assert cli._benchmark(args) == 0
    assert [row["run_id"] for row in json.loads(output.read_text())["results"]] == ["run-a", "run-b"]


def test_verify_manifest_and_audit_commands(monkeypatch, tmp_path, capsys) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli, "verify_manifest", lambda path, hmac_key="": path == manifest)
    assert cli._verify_manifest(argparse.Namespace(manifest=str(manifest), run_id="")) == 0
    monkeypatch.setattr(cli, "verify_manifest", lambda path, hmac_key="": False)
    assert cli._verify_manifest(argparse.Namespace(manifest=str(manifest), run_id="")) == 2
    monkeypatch.setattr(
        cli,
        "verify_audit_log",
        lambda path, secret: path.name == "events.log" and secret == "fixture-value",  # noqa: S105
    )
    args = argparse.Namespace(path="events.log", **{"secret": "fixture-value"})
    assert cli._verify_audit(args) == 0
    assert "audit chain valid" in capsys.readouterr().out
