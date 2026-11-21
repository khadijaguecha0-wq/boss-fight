"""Couche données : tout le SQL du projet se trouve ici.

Règles de cette couche :
- aucune règle de jeu (elles sont dans `src/logic/`) ;
- toutes les requêtes sont paramétrées (`?`), jamais de texte collé dans le SQL (BNF-02) ;
- chaque fonction qui écrit valide elle-même la transaction (`commit`), donc rien n'est
  perdu si l'application redémarre (BNF-04).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import DB_PATH
from src.logic.battle import BattleStatus
from src.logic.models import ChapterSummary, Mastery, MasteryRow, Question, User

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class UsernameTakenError(Exception):
    """Le pseudo existe déjà."""


class DuplicateQuestionError(Exception):
    """La même question existe déjà pour ce concept."""


# ---------- Connexion et création des tables ----------

def connect(db_path=DB_PATH) -> sqlite3.Connection:
    """Ouvre la base (la crée si le fichier n'existe pas). `":memory:"` donne une base temporaire."""
    conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ne vérifie les clés étrangères que sur demande
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Crée toutes les tables si elles n'existent pas encore."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _to_text(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment is not None else None


def _from_text(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


# ---------- Utilisateurs ----------

def create_user(
    conn: sqlite3.Connection, username: str, password_hash: str, role: str, now: datetime
) -> User:
    """Enregistre un utilisateur. Lève `UsernameTakenError` si le pseudo existe déjà."""
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, role, _to_text(now)),
        )
    except sqlite3.IntegrityError as error:
        conn.rollback()
        if "UNIQUE" in str(error):
            raise UsernameTakenError(username) from error
        raise
    conn.commit()
    return User(id=cursor.lastrowid, username=username, role=role)


def get_user_with_hash(conn: sqlite3.Connection, username: str) -> tuple[User, str] | None:
    """Renvoie (utilisateur, mot de passe haché) ou None si le pseudo est inconnu."""
    row = conn.execute(
        "SELECT id, username, role, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None
    return User(row["id"], row["username"], row["role"]), row["password_hash"]


# ---------- Chapitres et concepts ----------

def get_or_create_chapter(conn: sqlite3.Connection, title: str) -> int:
    """Renvoie l'identifiant du chapitre, en le créant s'il n'existe pas."""
    row = conn.execute("SELECT id FROM chapters WHERE title = ?", (title,)).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute("INSERT INTO chapters (title) VALUES (?)", (title,))
    conn.commit()
    return cursor.lastrowid


def _get_or_create_concept(conn: sqlite3.Connection, chapter_id: int, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM concepts WHERE chapter_id = ? AND name = ?", (chapter_id, name)
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO concepts (chapter_id, name) VALUES (?, ?)", (chapter_id, name)
    )
    return cursor.lastrowid


def list_chapters(conn: sqlite3.Connection) -> list[ChapterSummary]:
    """Liste les chapitres avec leur nombre de questions (BF-03)."""
    rows = conn.execute(
        """
        SELECT c.id, c.title, COUNT(q.id) AS question_count
        FROM chapters c
        LEFT JOIN concepts k ON k.chapter_id = c.id
        LEFT JOIN questions q ON q.concept_id = k.id
        GROUP BY c.id, c.title
        ORDER BY c.id
        """
    ).fetchall()
    return [ChapterSummary(r["id"], r["title"], r["question_count"]) for r in rows]


# ---------- Questions ----------

def add_question(
    conn: sqlite3.Connection,
    chapter_id: int,
    concept: str,
    text: str,
    options: tuple[str, str, str, str],
    correct_index: int,
    difficulty: str,
    explanation: str,
) -> int:
    """Ajoute une question (et son concept si besoin). Lève `DuplicateQuestionError` si elle existe."""
    concept_id = _get_or_create_concept(conn, chapter_id, concept)
    try:
        cursor = conn.execute(
            """
            INSERT INTO questions
                (concept_id, text, option_a, option_b, option_c, option_d,
                 correct_index, difficulty, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (concept_id, text, *options, correct_index, difficulty, explanation),
        )
    except sqlite3.IntegrityError as error:
        conn.rollback()
        if "UNIQUE" in str(error):
            raise DuplicateQuestionError(text) from error
        raise
    conn.commit()
    return cursor.lastrowid


def load_questions(conn: sqlite3.Connection, chapter_id: int) -> list[Question]:
    """Charge toutes les questions d'un chapitre sous forme d'objets `Question`."""
    rows = conn.execute(
        """
        SELECT q.id, q.text, q.option_a, q.option_b, q.option_c, q.option_d,
               q.correct_index, q.difficulty, q.explanation, k.name AS concept
        FROM questions q
        JOIN concepts k ON k.id = q.concept_id
        WHERE k.chapter_id = ?
        ORDER BY q.id
        """,
        (chapter_id,),
    ).fetchall()
    return [
        Question(
            id=r["id"],
            text=r["text"],
            options=(r["option_a"], r["option_b"], r["option_c"], r["option_d"]),
            correct_index=r["correct_index"],
            concept=r["concept"],
            difficulty=r["difficulty"],
            explanation=r["explanation"],
        )
        for r in rows
    ]


# ---------- Maîtrise des concepts ----------

def load_masteries(conn: sqlite3.Connection, user_id: int, chapter_id: int) -> dict[str, Mastery]:
    """Maîtrise connue d'un étudiant pour les concepts d'un chapitre (nom du concept -> Mastery).

    Les concepts jamais travaillés sont absents du dictionnaire : la logique les traite comme neufs.
    """
    rows = conn.execute(
        """
        SELECT k.name, m.theta, m.stability, m.last_review
        FROM mastery m
        JOIN concepts k ON k.id = m.concept_id
        WHERE m.user_id = ? AND k.chapter_id = ?
        """,
        (user_id, chapter_id),
    ).fetchall()
    return {
        r["name"]: Mastery(r["theta"], r["stability"], _from_text(r["last_review"])) for r in rows
    }


def save_mastery(
    conn: sqlite3.Connection, user_id: int, chapter_id: int, concept: str, mastery: Mastery
) -> None:
    """Enregistre (ou met à jour) la maîtrise d'un étudiant pour un concept."""
    row = conn.execute(
        "SELECT id FROM concepts WHERE chapter_id = ? AND name = ?", (chapter_id, concept)
    ).fetchone()
    if row is None:
        raise LookupError(f"Concept inconnu dans ce chapitre : {concept!r}")
    conn.execute(
        """
        INSERT INTO mastery (user_id, concept_id, theta, stability, last_review)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (user_id, concept_id) DO UPDATE SET
            theta = excluded.theta,
            stability = excluded.stability,
            last_review = excluded.last_review
        """,
        (user_id, row["id"], mastery.theta, mastery.stability, _to_text(mastery.last_review)),
    )
    conn.commit()


def list_mastery_rows(conn: sqlite3.Connection, user_id: int) -> list[MasteryRow]:
    """Toutes les maîtrises d'un étudiant, pour le tableau de bord (BF-08)."""
    rows = conn.execute(
        """
        SELECT c.title, k.name, m.theta, m.stability, m.last_review
        FROM mastery m
        JOIN concepts k ON k.id = m.concept_id
        JOIN chapters c ON c.id = k.chapter_id
        WHERE m.user_id = ?
        ORDER BY c.id, k.id
        """,
        (user_id,),
    ).fetchall()
    return [
        MasteryRow(r["title"], r["name"], Mastery(r["theta"], r["stability"], _from_text(r["last_review"])))
        for r in rows
    ]


# ---------- Combats et réponses ----------

def start_battle(conn: sqlite3.Connection, user_id: int, chapter_id: int, now: datetime) -> int:
    """Enregistre le début d'un combat et renvoie son identifiant."""
    cursor = conn.execute(
        "INSERT INTO battles (user_id, chapter_id, started_at) VALUES (?, ?, ?)",
        (user_id, chapter_id, _to_text(now)),
    )
    conn.commit()
    return cursor.lastrowid


def record_answer(
    conn: sqlite3.Connection,
    battle_id: int,
    question_id: int,
    chosen_index: int,
    is_correct: bool,
    now: datetime,
) -> None:
    """Enregistre une réponse donnée pendant un combat."""
    conn.execute(
        """
        INSERT INTO answers (battle_id, question_id, chosen_index, is_correct, answered_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (battle_id, question_id, chosen_index, int(is_correct), _to_text(now)),
    )
    conn.commit()


def finish_battle(
    conn: sqlite3.Connection,
    battle_id: int,
    status: BattleStatus,
    boss_hp: int,
    lives: int,
    correct_count: int,
    answered_count: int,
    mean_mastery: float,
    now: datetime,
) -> None:
    """Enregistre la fin d'un combat : résultat, score et maîtrise moyenne."""
    conn.execute(
        """
        UPDATE battles
        SET ended_at = ?, status = ?, boss_hp = ?, lives = ?,
            correct_count = ?, answered_count = ?, mean_mastery = ?
        WHERE id = ?
        """,
        (
            _to_text(now),
            status.name.lower(),  # EN_COURS -> "en_cours", VICTOIRE -> "victoire", DEFAITE -> "defaite"
            boss_hp,
            lives,
            correct_count,
            answered_count,
            mean_mastery,
            battle_id,
        ),
    )
    conn.commit()


def get_battle(conn: sqlite3.Connection, battle_id: int) -> sqlite3.Row | None:
    """Renvoie la ligne d'un combat (utile pour vérifier ce qui a été enregistré)."""
    return conn.execute("SELECT * FROM battles WHERE id = ?", (battle_id,)).fetchone()


def list_answers(conn: sqlite3.Connection, battle_id: int) -> list[sqlite3.Row]:
    """Réponses d'un combat, dans l'ordre où elles ont été données."""
    return conn.execute(
        "SELECT * FROM answers WHERE battle_id = ? ORDER BY id", (battle_id,)
    ).fetchall()


def mastery_history(conn: sqlite3.Connection, user_id: int) -> list[tuple[datetime, float]]:
    """Maîtrise moyenne à la fin de chaque combat terminé, du plus ancien au plus récent (BF-09)."""
    rows = conn.execute(
        """
        SELECT ended_at, mean_mastery
        FROM battles
        WHERE user_id = ? AND ended_at IS NOT NULL AND mean_mastery IS NOT NULL
        ORDER BY ended_at
        """,
        (user_id,),
    ).fetchall()
    return [(datetime.fromisoformat(r["ended_at"]), r["mean_mastery"]) for r in rows]
