"""Initialisation de l'application : tables, comptes de démonstration et banque de questions.

Ce code peut être relancé sans danger : ce qui existe déjà n'est jamais recréé ni dupliqué.
Il sert aussi à reconstruire la démonstration si l'hébergeur gratuit efface la base (voir le
risque identifié dans le cahier des charges).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.config import (
    ADMIN_USERNAME,
    DEFAULT_BANK_PATH,
    DEFAULT_CHAPTER_TITLE,
    DEMO_USERNAME,
    ROLE_ADMIN,
    ROLE_STUDENT,
)
from src.data import repository
from src.logic import auth, importer


@dataclass
class BootstrapSummary:
    """Ce que l'initialisation a réellement créé (pour l'afficher à l'utilisateur)."""

    admin_created: bool = False
    demo_created: bool = False
    questions_imported: int = 0
    chapter_title: str | None = None


def _ensure_account(conn, username, password, role, now) -> bool:
    """Crée le compte s'il n'existe pas. Renvoie True si on vient de le créer."""
    if repository.get_user_with_hash(conn, username) is not None:
        return False
    auth.register(conn, username, password, role=role, now=now)
    return True


def initialize_database(
    conn: sqlite3.Connection,
    admin_password: str,
    demo_password: str,
    bank_path: Path | str = DEFAULT_BANK_PATH,
    chapter_title: str = DEFAULT_CHAPTER_TITLE,
    now: datetime | None = None,
) -> BootstrapSummary:
    """Prépare une base prête à l'emploi : tables, administrateur, compte de démonstration, questions."""
    now = now or datetime.now()
    summary = BootstrapSummary()

    repository.init_db(conn)
    summary.admin_created = _ensure_account(conn, ADMIN_USERNAME, admin_password, ROLE_ADMIN, now)
    summary.demo_created = _ensure_account(conn, DEMO_USERNAME, demo_password, ROLE_STUDENT, now)

    already_loaded = any(c.title == chapter_title and c.question_count > 0
                         for c in repository.list_chapters(conn))
    if not already_loaded:
        admin, _ = repository.get_user_with_hash(conn, ADMIN_USERNAME)  # l'import exige un administrateur
        content = importer.decode_upload(Path(bank_path).read_bytes())
        fmt = importer.detect_format(str(bank_path))
        report = importer.import_questions(conn, admin, chapter_title, content, fmt)
        if report.file_error:
            raise RuntimeError(f"Banque de questions illisible : {report.file_error}")
        summary.questions_imported = report.imported
        summary.chapter_title = chapter_title
    return summary
