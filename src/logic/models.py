"""Objets métier de base : utilisateur, question, maîtrise d'un concept."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import DIFFICULTY_VALUE, INITIAL_STABILITY, INITIAL_THETA, ROLE_ADMIN


@dataclass(frozen=True)
class Question:
    """Une question à choix multiples liée à un concept.

    `options` est un tuple de textes ; `correct_index` est la position (à partir
    de 0) de la bonne réponse. `difficulty` vaut « facile », « moyen » ou « difficile ».
    """

    id: int
    text: str
    options: tuple
    correct_index: int
    concept: str
    difficulty: str
    explanation: str = ""

    def __post_init__(self) -> None:
        if self.difficulty not in DIFFICULTY_VALUE:
            raise ValueError(f"Difficulté inconnue : {self.difficulty!r}")
        if not 0 <= self.correct_index < len(self.options):
            raise ValueError("L'indice de la bonne réponse est hors des options.")

    def is_correct(self, choice: int) -> bool:
        """Indique si l'option choisie (indice à partir de 0) est la bonne."""
        return choice == self.correct_index


@dataclass(frozen=True)
class Mastery:
    """Maîtrise d'un concept par un étudiant.

    - `theta` : niveau estimé de l'étudiant sur ce concept ;
    - `stability` : stabilité de la mémoire, en jours (plus elle est grande, plus on oublie lentement) ;
    - `last_review` : date de la dernière révision, ou None si le concept n'a jamais été révisé.
    """

    theta: float = INITIAL_THETA
    stability: float = INITIAL_STABILITY
    last_review: datetime | None = None


@dataclass(frozen=True)
class User:
    """Un utilisateur connecté (le mot de passe haché n'est jamais conservé ici)."""

    id: int
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        """Vrai pour l'administrateur, seul autorisé à importer des questions (BF-10)."""
        return self.role == ROLE_ADMIN


@dataclass(frozen=True)
class ChapterSummary:
    """Un chapitre et son nombre de questions, pour l'écran de choix (BF-03)."""

    id: int
    title: str
    question_count: int


@dataclass(frozen=True)
class MasteryRow:
    """Maîtrise d'un concept pour le tableau de bord (BF-08)."""

    chapter_title: str
    concept: str
    mastery: Mastery


@dataclass(frozen=True)
class ConceptProgress:
    """Un concept d'un chapitre avec la maîtrise de l'étudiant (None s'il ne l'a jamais travaillé)."""

    chapter_title: str
    concept: str
    mastery: Mastery | None
