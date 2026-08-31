from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _OpenAICompatibleHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length))
        content = '{"risk": 1, "verdict": "ok"}' if payload.get("response_format") else "I cannot help with that request."
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True)  # noqa: S603 -- fixed test commands


def _install_distribution(environment_dir: Path, distribution: Path, repo_root: Path) -> Path:
    _run([sys.executable, "-m", "venv", str(environment_dir)], cwd=repo_root)
    pip = environment_dir / "bin" / "pip"
    _run([str(pip), "install", "-r", str(repo_root / "requirements.runtime.lock")], cwd=repo_root)
    _run([str(pip), "install", "--no-deps", str(distribution)], cwd=repo_root)
    return environment_dir / "bin" / "vendor-rtp"


def test_wheel_and_sdist_include_assets_and_installed_cli_runs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = tmp_path / "dist"
    _run([sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist_dir)], cwd=repo_root)
    wheel = next(dist_dir.glob("*.whl"))
    sdist = next(dist_dir.glob("*.tar.gz"))

    with tarfile.open(sdist) as archive:
        names = archive.getnames()
    assert any(name.endswith("apps/api/resources/cases/cases.v1.json") for name in names)
    assert any(name.endswith("apps/api/resources/profiles/quick_gates.yaml") for name in names)
    assert any(name.endswith("apps/api/templates/passport.html.j2") for name in names)

    outside = tmp_path / "outside"
    outside.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAICompatibleHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cli = _install_distribution(tmp_path / "wheel-env", wheel, repo_root)
        env = {
            **os.environ,
            "FEATHERLESS_API_KEY": "packaged-test-key",
            "VENDOR_RTP_REPORTS_DIR": str(outside / "reports"),
        }
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        _run(
            [
                str(cli),
                "run",
                "--profile",
                "quick_gates",
                "--base-url",
                base_url,
                "--model",
                "mock-model",
                "--run-id",
                "packaged-run",
            ],
            cwd=outside,
            env=env,
        )
        _run([str(cli), "verify-manifest", "--run-id", "packaged-run"], cwd=outside, env=env)
        assert (outside / "reports" / "runs" / "packaged-run" / "passport.json").is_file()
        assert (outside / "reports" / "runs" / "packaged-run" / "passport.html").is_file()

        sdist_cli = _install_distribution(tmp_path / "sdist-env", sdist, repo_root)
        _run([str(sdist_cli), "--help"], cwd=outside, env=env)
        _run(
            [
                str(sdist_cli),
                "run",
                "--profile",
                "quick_gates",
                "--base-url",
                base_url,
                "--model",
                "mock-model",
                "--run-id",
                "sdist-run",
            ],
            cwd=outside,
            env=env,
        )
        assert (outside / "reports" / "runs" / "sdist-run" / "manifest.json").is_file()
    finally:
        server.shutdown()
        server.server_close()
