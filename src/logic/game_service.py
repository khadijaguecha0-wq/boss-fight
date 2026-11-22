"""Service de jeu : relie les règles du combat, le choix des questions et la base de données.

L'interface (Streamlit) n'appelle que ces fonctions : elle ne contient aucune règle de jeu
(BNF-05). Chaque réponse est enregistrée immédiatement en base, donc rien n'est perdu si
l'application s'arrête en plein combat (BNF-04).
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from src.config import WEAK_THRESHOLD
from src.data import repository
from src.logic.battle import AnswerResult, Battle, BattleStatus
from src.logic.memory_model import mastery_percent, recall_probability
from src.logic.models import ChapterSummary, Mastery, Question, User
from src.logic.selector import choose_question

STATUS_NOT_EVALUATED = "Non évalué"
STATUS_TO_REVIEW = "À revoir"
STATUS_MASTERED = "Maîtrisé"


class GameError(Exception):
    """Action impossible dans l'état actuel du combat ; le message est affichable à l'étudiant."""


@dataclass
class BattleSession:
    """Tout ce qu'il faut garder en mémoire pendant un combat (l'interface le range dans `session_state`)."""

    user: User
    chapter: ChapterSummary
    battle_id: int
    battle: Battle
    questions: list
    rng: random.Random = field(default_factory=random.Random)
    current: Question | None = None        # question affichée en ce moment
    last_result: AnswerResult | None = None  # résultat de la réponse à la question courante
    finished: bool = False                  # fin de combat déjà enregistrée en base
    summary: "BattleSummary | None" = None


@dataclass(frozen=True)
class BattleSummary:
    """Ce que l'écran de résultat affiche (BF-07)."""

    victory: bool
    boss_hp: int
    lives: int
    correct_count: int
    answered_count: int
    weak_concepts: list  # couples (concept, pourcentage de maîtrise), du plus faible au plus fort


@dataclass(frozen=True)
class ConceptLine:
    """Une ligne du tableau de bord : maîtrise d'un concept (BF-08)."""

    chapter_title: str
    concept: str
    percent: float | None        # None si le concept n'a jamais été travaillé
    retention: float | None      # chance de s'en souvenir maintenant, en % (courbe d'oubli)
    last_review: datetime | None
    status: str


# ---------- Lecture pour les écrans ----------

def list_chapters(conn: sqlite3.Connection) -> list[ChapterSummary]:
    """Chapitres disponibles avec leur nombre de questions (BF-03)."""
    return repository.list_chapters(conn)


def concept_lines(conn: sqlite3.Connection, user: User, now: datetime | None = None) -> list[ConceptLine]:
    """Maîtrise de l'étudiant pour chaque concept, jamais travaillés compris (BF-08)."""
    now = now or datetime.now()
    lines = []
    for item in repository.list_concept_progress(conn, user.id):
        mastery = item.mastery
        if mastery is None or mastery.last_review is None:
            lines.append(ConceptLine(item.chapter_title, item.concept, None, None, None, STATUS_NOT_EVALUATED))
            continue
        percent = mastery_percent(mastery)
        status = STATUS_TO_REVIEW if percent < WEAK_THRESHOLD else STATUS_MASTERED
        retention = 100.0 * recall_probability(mastery, now)
        lines.append(ConceptLine(item.chapter_title, item.concept, percent, retention, mastery.last_review, status))
    return lines


def progress_points(conn: sqlite3.Connection, user: User) -> list[tuple[datetime, float]]:
    """Maîtrise moyenne à la fin de chaque combat terminé, pour la courbe de progression (BF-09)."""
    return repository.mastery_history(conn, user.id)


# ---------- Déroulement d'un combat ----------

def start_battle(
    conn: sqlite3.Connection,
    user: User,
    chapter_id: int,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> BattleSession:
    """Prépare un combat sur un chapitre et choisit la première question (BF-03, BF-06)."""
    now = now or datetime.now()
    chapter = next((c for c in repository.list_chapters(conn) if c.id == chapter_id), None)
    if chapter is None:
        raise GameError("Ce chapitre n'existe pas.")
    if chapter.question_count == 0:
        raise GameError("Ce chapitre ne contient encore aucune question.")

    questions = repository.load_questions(conn, chapter_id)
    battle = Battle(masteries=repository.load_masteries(conn, user.id, chapter_id))
    session = BattleSession(
        user=user,
        chapter=chapter,
        battle_id=repository.start_battle(conn, user.id, chapter_id, now),
        battle=battle,
        questions=questions,
        rng=rng or random.Random(),
    )
    session.current = choose_question(questions, battle.masteries, battle.asked_ids, now=now, rng=session.rng)
    return session


def submit_answer(
    conn: sqlite3.Connection, session: BattleSession, choice: int, now: datetime | None = None
) -> AnswerResult:
    """Applique la réponse de l'étudiant, l'enregistre, et termine le combat si le boss ou le joueur tombe."""
    if session.current is None or session.battle.is_over():
        raise GameError("Il n'y a pas de question en cours.")
    if session.last_result is not None:
        raise GameError("Cette question a déjà reçu une réponse.")

    now = now or datetime.now()
    question = session.current
    try:
        result = session.battle.apply_answer(question, choice, now)
    except ValueError as error:
        raise GameError(str(error)) from error

    repository.record_answer(conn, session.battle_id, question.id, choice, result.correct, now)
    repository.save_mastery(conn, session.user.id, session.chapter.id, question.concept, result.new_mastery)
    session.last_result = result
    if session.battle.is_over():
        finish_battle(conn, session, now)
    return result


def next_question(
    conn: sqlite3.Connection,
    session: BattleSession,
    now: datetime | None = None,
) -> Question | None:
    """Passe à la question suivante. Renvoie None si le combat est terminé (y compris faute de questions)."""
    if session.last_result is None and session.current is not None:
        raise GameError("Réponds d'abord à la question en cours.")
    now = now or datetime.now()
    battle = session.battle

    if not battle.is_over():
        question = choose_question(session.questions, battle.masteries, battle.asked_ids, now=now, rng=session.rng)
        if question is not None:
            session.current = question
            session.last_result = None
            return question
        battle.mark_questions_exhausted()  # plus de question et le boss est en vie : défaite

    session.current = None
    session.last_result = None
    finish_battle(conn, session, now)
    return None


def finish_battle(conn: sqlite3.Connection, session: BattleSession, now: datetime | None = None) -> BattleSummary:
    """Enregistre la fin du combat (une seule fois) et renvoie le résumé du résultat (BF-07, BF-09)."""
    battle = session.battle
    if not battle.is_over():
        raise GameError("Le combat n'est pas terminé.")
    if session.finished and session.summary is not None:
        return session.summary

    now = now or datetime.now()
    concepts = sorted({q.concept for q in session.questions})
    mean = sum(mastery_percent(battle.masteries.get(c, Mastery())) for c in concepts) / len(concepts)
    repository.finish_battle(
        conn, session.battle_id, battle.status, battle.boss_hp, battle.lives,
        battle.correct_count, battle.answered_count, mean, now,
    )
    session.finished = True
    session.summary = BattleSummary(
        victory=battle.status == BattleStatus.VICTOIRE,
        boss_hp=battle.boss_hp,
        lives=battle.lives,
        correct_count=battle.correct_count,
        answered_count=battle.answered_count,
        weak_concepts=battle.weak_concepts(),
    )
    return session.summary
