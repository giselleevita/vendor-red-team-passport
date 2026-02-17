from __future__ import annotations

import datetime as dt
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
from threading import Lock

from apps.api.config import get_settings
from apps.api.services.run_store import reports_dir, validate_run_id


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat()


def jobs_dir() -> Path:
    d = reports_dir() / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _job_path(job_id: str) -> Path:
    return jobs_dir() / f"{validate_run_id(job_id)}.json"


def _base_job(job_id: str, payload: dict) -> dict:
    created = _utc_now_iso()
    base = {
        "job_id": validate_run_id(job_id),
        "status": "queued",
        "created_at_utc": created,
        "started_at_utc": None,
        "finished_at_utc": None,
        "updated_at_utc": created,
    }
    base.update(payload)
    return base


class FileJobStore:
    def create_job(self, job_id: str, payload: dict) -> dict:
        p = _job_path(job_id)
        base = _base_job(job_id, payload)
        p.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
        return base

    def load_job(self, job_id: str) -> dict | None:
        p = _job_path(job_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def update_job(self, job_id: str, patch: dict) -> dict:
        cur = self.load_job(job_id)
        if cur is None:
            raise FileNotFoundError(f"job not found: {job_id}")
        cur.update(patch)
        cur["updated_at_utc"] = _utc_now_iso()
        _job_path(job_id).write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
        return cur


class SqlJobStore:
    def __init__(self, dsn: str) -> None:
        raw = dsn.strip()
        self.dsn = raw or self._default_sqlite_dsn()
        self.is_sqlite = self.dsn.startswith("sqlite:///")
        self.is_postgres = self.dsn.startswith("postgresql://") or self.dsn.startswith("postgres://")
        if not (self.is_sqlite or self.is_postgres):
            raise ValueError("unsupported JOB_STORE_DSN; expected sqlite:///... or postgresql://...")
        self._init_lock = Lock()
        self._initialized = False

    def _default_sqlite_dsn(self) -> str:
        p = (reports_dir() / "jobs.db").resolve()
        return f"sqlite:///{p}"

    def _sqlite_path(self) -> Path:
        return Path(self.dsn.removeprefix("sqlite:///")).expanduser().resolve()

    def _connect_sqlite(self) -> sqlite3.Connection:
        p = self._sqlite_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_postgres(self):
        try:
            import psycopg
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("psycopg is required for postgresql JOB_STORE_DSN") from e
        return psycopg.connect(self.dsn)

    def _ensure_schema(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            if self.is_sqlite:
                conn = self._connect_sqlite()
                try:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS jobs (
                          job_id TEXT PRIMARY KEY,
                          payload_json TEXT NOT NULL,
                          tenant_id TEXT NOT NULL,
                          run_id TEXT NOT NULL,
                          status TEXT NOT NULL,
                          created_at_utc TEXT NOT NULL,
                          started_at_utc TEXT,
                          finished_at_utc TEXT,
                          updated_at_utc TEXT NOT NULL
                        )
                        """
                    )
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at_utc)")
                    conn.commit()
                finally:
                    conn.close()
            else:
                conn = self._connect_postgres()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS jobs (
                              job_id TEXT PRIMARY KEY,
                              payload_json TEXT NOT NULL,
                              tenant_id TEXT NOT NULL,
                              run_id TEXT NOT NULL,
                              status TEXT NOT NULL,
                              created_at_utc TEXT NOT NULL,
                              started_at_utc TEXT,
                              finished_at_utc TEXT,
                              updated_at_utc TEXT NOT NULL
                            )
                            """
                        )
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id)")
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at_utc)")
                    conn.commit()
                finally:
                    conn.close()
            self._initialized = True

    def create_job(self, job_id: str, payload: dict) -> dict:
        self._ensure_schema()
        base = _base_job(job_id, payload)
        tenant_id = str(base.get("tenant_id", "")).strip()
        run_id = str(base.get("run_id", "")).strip()
        status = str(base.get("status", "queued")).strip() or "queued"
        body = json.dumps(base, separators=(",", ":"), ensure_ascii=True)
        if self.is_sqlite:
            conn = self._connect_sqlite()
            try:
                conn.execute(
                    """
                    INSERT INTO jobs(job_id, payload_json, tenant_id, run_id, status, created_at_utc, started_at_utc, finished_at_utc, updated_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        base["job_id"],
                        body,
                        tenant_id,
                        run_id,
                        status,
                        base["created_at_utc"],
                        base.get("started_at_utc"),
                        base.get("finished_at_utc"),
                        base["updated_at_utc"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        else:
            conn = self._connect_postgres()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO jobs(job_id, payload_json, tenant_id, run_id, status, created_at_utc, started_at_utc, finished_at_utc, updated_at_utc)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            base["job_id"],
                            body,
                            tenant_id,
                            run_id,
                            status,
                            base["created_at_utc"],
                            base.get("started_at_utc"),
                            base.get("finished_at_utc"),
                            base["updated_at_utc"],
                        ),
                    )
                conn.commit()
            finally:
                conn.close()
        return base

    def load_job(self, job_id: str) -> dict | None:
        self._ensure_schema()
        jid = validate_run_id(job_id)
        if self.is_sqlite:
            conn = self._connect_sqlite()
            try:
                row = conn.execute("SELECT payload_json FROM jobs WHERE job_id = ?", (jid,)).fetchone()
                if row is None:
                    return None
                return json.loads(str(row["payload_json"]))
            finally:
                conn.close()
        conn = self._connect_postgres()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM jobs WHERE job_id = %s", (jid,))
                row = cur.fetchone()
                if row is None:
                    return None
                return json.loads(str(row[0]))
        finally:
            conn.close()

    def update_job(self, job_id: str, patch: dict) -> dict:
        cur = self.load_job(job_id)
        if cur is None:
            raise FileNotFoundError(f"job not found: {job_id}")
        cur.update(patch)
        cur["updated_at_utc"] = _utc_now_iso()

        tenant_id = str(cur.get("tenant_id", "")).strip()
        run_id = str(cur.get("run_id", "")).strip()
        status = str(cur.get("status", "")).strip()
        body = json.dumps(cur, separators=(",", ":"), ensure_ascii=True)

        if self.is_sqlite:
            conn = self._connect_sqlite()
            try:
                conn.execute(
                    """
                    UPDATE jobs
                    SET payload_json = ?, tenant_id = ?, run_id = ?, status = ?, started_at_utc = ?, finished_at_utc = ?, updated_at_utc = ?
                    WHERE job_id = ?
                    """,
                    (
                        body,
                        tenant_id,
                        run_id,
                        status,
                        cur.get("started_at_utc"),
                        cur.get("finished_at_utc"),
                        cur["updated_at_utc"],
                        cur["job_id"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            return cur

        conn = self._connect_postgres()
        try:
            with conn.cursor() as cur_db:
                cur_db.execute(
                    """
                    UPDATE jobs
                    SET payload_json = %s, tenant_id = %s, run_id = %s, status = %s, started_at_utc = %s, finished_at_utc = %s, updated_at_utc = %s
                    WHERE job_id = %s
                    """,
                    (
                        body,
                        tenant_id,
                        run_id,
                        status,
                        cur.get("started_at_utc"),
                        cur.get("finished_at_utc"),
                        cur["updated_at_utc"],
                        cur["job_id"],
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return cur


@lru_cache(maxsize=1)
def get_job_store():
    settings = get_settings()
    backend = (settings.job_store_backend or "file").strip().lower()
    if backend == "file":
        return FileJobStore()
    if backend == "sql":
        return SqlJobStore(settings.job_store_dsn)
    raise ValueError("unsupported JOB_STORE_BACKEND; expected 'file' or 'sql'")


def create_job(job_id: str, payload: dict) -> dict:
    return get_job_store().create_job(job_id, payload)


def load_job(job_id: str) -> dict | None:
    return get_job_store().load_job(job_id)


def update_job(job_id: str, patch: dict) -> dict:
    return get_job_store().update_job(job_id, patch)
