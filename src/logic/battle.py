"""Règles du combat : points de vie du boss, vies du joueur, fin de partie (BF-04 à BF-07)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.config import (
    BOSS_HP,
    DAMAGE_BY_DIFFICULTY,
    DIFFICULTY_VALUE,
    PLAYER_LIVES,
    WEAK_THRESHOLD,
)
from src.logic.memory_model import mastery_percent, update_mastery
from src.logic.models import Mastery, Question


class BattleStatus(Enum):
    """État d'un combat."""

    EN_COURS = "en cours"
    VICTOIRE = "victoire"
    DEFAITE = "défaite"


@dataclass(frozen=True)
class AnswerResult:
    """Ce que l'interface doit afficher après une réponse (BF-05)."""

    question_id: int
    concept: str
    correct: bool
    damage: int            # PV réellement retirés au boss
    lives_lost: int        # 0 ou 1
    correct_index: int
    explanation: str
    new_mastery: Mastery   # à enregistrer en base par la couche données


@dataclass
class Battle:
    """Un combat entre l'étudiant et un boss (un chapitre).

    `masteries` contient la maîtrise de l'étudiant pour chaque concept (nom du concept
    vers `Mastery`). Elle est mise à jour après chaque réponse.
    """

    masteries: dict = field(default_factory=dict)
    boss_hp: int = BOSS_HP
    lives: int = PLAYER_LIVES
    status: BattleStatus = BattleStatus.EN_COURS
    asked_ids: set = field(default_factory=set)
    correct_count: int = 0
    answered_count: int = 0
    touched_concepts: list = field(default_factory=list)

    def is_over(self) -> bool:
        """Vrai si le combat est terminé (victoire ou défaite)."""
        return self.status != BattleStatus.EN_COURS

    def apply_answer(
        self, question: Question, choice: int, now: datetime | None = None
    ) -> AnswerResult:
        """Applique la réponse de l'étudiant et renvoie le résultat à afficher.

        Une bonne réponse retire des PV au boss (10, 15 ou 20 selon la difficulté) ;
        une mauvaise réponse retire une vie au joueur. La maîtrise du concept est mise à jour.
        """
        if self.is_over():
            raise ValueError("Le combat est terminé.")
        if question.id in self.asked_ids:
            raise ValueError("Cette question a déjà été posée dans ce combat.")
        if not 0 <= choice < len(question.options):
            raise ValueError("Option choisie invalide.")

        now = now or datetime.now()
        correct = question.is_correct(choice)

        damage = 0
        lives_lost = 0
        if correct:
            damage = min(DAMAGE_BY_DIFFICULTY[question.difficulty], self.boss_hp)
            self.boss_hp -= damage
            self.correct_count += 1
        else:
            lives_lost = 1
            self.lives -= 1

        self.asked_ids.add(question.id)
        self.answered_count += 1
        if question.concept not in self.touched_concepts:
            self.touched_concepts.append(question.concept)

        old = self.masteries.get(question.concept, Mastery())
        new = update_mastery(old, correct, DIFFICULTY_VALUE[question.difficulty], now)
        self.masteries[question.concept] = new

        if self.boss_hp <= 0:
            self.status = BattleStatus.VICTOIRE
        elif self.lives <= 0:
            self.status = BattleStatus.DEFAITE

        return AnswerResult(
            question_id=question.id,
            concept=question.concept,
            correct=correct,
            damage=damage,
            lives_lost=lives_lost,
            correct_index=question.correct_index,
            explanation=question.explanation,
            new_mastery=new,
        )

    def mark_questions_exhausted(self) -> None:
        """Termine le combat quand il n'y a plus de question : défaite si le boss est encore en vie."""
        if self.status == BattleStatus.EN_COURS:
            self.status = BattleStatus.DEFAITE

    def weak_concepts(self) -> list:
        """Concepts travaillés dans ce combat dont la maîtrise est sous 60 % (BF-07).

        Renvoie une liste de couples (concept, pourcentage), du plus faible au plus fort.
        """
        weak = []
        for concept in self.touched_concepts:
            percent = mastery_percent(self.masteries[concept])
            if percent < WEAK_THRESHOLD:
                weak.append((concept, percent))
        return sorted(weak, key=lambda pair: pair[1])
