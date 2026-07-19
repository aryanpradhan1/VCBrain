"""Small SQLite memory layer for applications, analysis, documents, and sources.

The scoring contracts remain their own immutable payloads.  This module stores the
application context around those payloads so an opportunity can be rendered and
audited after a server restart without retaining raw web pages.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApplicationStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                  company_id TEXT PRIMARY KEY,
                  founder_id TEXT NOT NULL,
                  company_name TEXT NOT NULL,
                  status TEXT NOT NULL,
                  submitted_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  profile_json TEXT NOT NULL DEFAULT '{}',
                  signal_json TEXT,
                  analysis_json TEXT,
                  documents_json TEXT NOT NULL DEFAULT '[]',
                  sources_json TEXT NOT NULL DEFAULT '[]',
                  trace_json TEXT NOT NULL DEFAULT '[]',
                  error_message TEXT,
                  decision TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS thesis_settings (
                  settings_key TEXT PRIMARY KEY,
                  config_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                  session_id TEXT PRIMARY KEY,
                  company_id TEXT NOT NULL,
                  founder_id TEXT NOT NULL,
                  status TEXT NOT NULL,
                  questions_json TEXT NOT NULL DEFAULT '[]',
                  responses_json TEXT NOT NULL DEFAULT '[]',
                  result_json TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _load(value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def upsert_application(
        self,
        *,
        company_id: str,
        founder_id: str,
        company_name: str,
        status: str,
        profile: dict[str, Any],
        documents: list[dict[str, Any]],
        sources: list[dict[str, Any]],
        signal: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        trace: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO applications (
                  company_id, founder_id, company_name, status, submitted_at, updated_at,
                  profile_json, signal_json, analysis_json, documents_json, sources_json,
                  trace_json, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                  founder_id=excluded.founder_id,
                  company_name=excluded.company_name,
                  status=excluded.status,
                  updated_at=excluded.updated_at,
                  profile_json=excluded.profile_json,
                  signal_json=COALESCE(excluded.signal_json, applications.signal_json),
                  analysis_json=COALESCE(excluded.analysis_json, applications.analysis_json),
                  documents_json=excluded.documents_json,
                  sources_json=excluded.sources_json,
                  trace_json=excluded.trace_json,
                  error_message=excluded.error_message
                """,
                (
                    company_id,
                    founder_id,
                    company_name,
                    status,
                    now,
                    now,
                    self._json(profile),
                    self._json(signal) if signal is not None else None,
                    self._json(analysis) if analysis is not None else None,
                    self._json(documents),
                    self._json(sources),
                    self._json(trace or []),
                    error_message,
                ),
            )

    def update_processing(
        self,
        company_id: str,
        *,
        status: str,
        signal: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        documents: list[dict[str, Any]] | None = None,
        sources: list[dict[str, Any]] | None = None,
        trace: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> None:
        current = self.get(company_id)
        if current is None:
            raise KeyError(company_id)
        self.upsert_application(
            company_id=company_id,
            founder_id=current["founder_id"],
            company_name=current["company_name"],
            status=status,
            profile=current["profile"],
            documents=documents if documents is not None else current["documents"],
            sources=sources if sources is not None else current["sources"],
            signal=signal,
            analysis=analysis,
            trace=trace if trace is not None else current["trace"],
            error_message=error_message,
        )

    def get(self, company_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM applications WHERE company_id = ?", (company_id,)
            ).fetchone()
        return self._row(row) if row else None

    def all(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM applications ORDER BY submitted_at DESC"
            ).fetchall()
        return [self._row(row) for row in rows]

    def set_decision(self, company_id: str, decision: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE applications SET decision = ?, updated_at = ? WHERE company_id = ?",
                (decision, utc_now(), company_id),
            )

    def get_by_founder(self, founder_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM applications WHERE founder_id = ? ORDER BY updated_at DESC LIMIT 1",
                (founder_id,),
            ).fetchone()
        return self._row(row) if row else None

    def get_thesis(self, default: dict[str, Any]) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT config_json FROM thesis_settings WHERE settings_key = 'fund'"
            ).fetchone()
        return self._load(row["config_json"], default) if row else default

    def set_thesis(self, config: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO thesis_settings (settings_key, config_json, updated_at)
                VALUES ('fund', ?, ?)
                ON CONFLICT(settings_key) DO UPDATE SET config_json=excluded.config_json, updated_at=excluded.updated_at
                """,
                (self._json(config), now),
            )
        return config

    def create_interview(self, *, session_id: str, company_id: str, founder_id: str, first_question: str) -> dict[str, Any]:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO interview_sessions (
                  session_id, company_id, founder_id, status, questions_json, responses_json, created_at, updated_at
                ) VALUES (?, ?, ?, 'active', ?, '[]', ?, ?)
                """,
                (session_id, company_id, founder_id, self._json([first_question]), now, now),
            )
        return self.get_interview(session_id) or {}

    def get_active_interview(self, founder_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM interview_sessions
                WHERE founder_id = ? AND status = 'active'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (founder_id,),
            ).fetchone()
        return self._interview_row(row) if row else None

    def get_latest_interview(self, founder_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM interview_sessions
                WHERE founder_id = ?
                ORDER BY updated_at DESC LIMIT 1
                """,
                (founder_id,),
            ).fetchone()
        return self._interview_row(row) if row else None

    def get_interview(self, session_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return self._interview_row(row) if row else None

    def update_interview(
        self,
        session_id: str,
        *,
        status: str,
        questions: list[str],
        responses: list[str],
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE interview_sessions
                SET status=?, questions_json=?, responses_json=?, result_json=?, updated_at=?
                WHERE session_id=?
                """,
                (status, self._json(questions), self._json(responses), self._json(result) if result else None, utc_now(), session_id),
            )
        return self.get_interview(session_id) or {}

    def _row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "company_id": row["company_id"],
            "founder_id": row["founder_id"],
            "company_name": row["company_name"],
            "status": row["status"],
            "submitted_at": row["submitted_at"],
            "updated_at": row["updated_at"],
            "profile": self._load(row["profile_json"], {}),
            "signal": self._load(row["signal_json"], None),
            "analysis": self._load(row["analysis_json"], None),
            "documents": self._load(row["documents_json"], []),
            "sources": self._load(row["sources_json"], []),
            "trace": self._load(row["trace_json"], []),
            "error_message": row["error_message"],
            "decision": row["decision"],
        }

    def _interview_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "session_id": row["session_id"],
            "company_id": row["company_id"],
            "founder_id": row["founder_id"],
            "status": row["status"],
            "questions": self._load(row["questions_json"], []),
            "responses": self._load(row["responses_json"], []),
            "result": self._load(row["result_json"], None),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
