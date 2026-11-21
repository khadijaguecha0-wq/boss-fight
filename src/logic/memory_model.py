"""Modèle d'adaptation : courbe d'oubli et niveau de l'étudiant (BF-06, BNF-08).

Deux formules, décrites dans le cahier des charges :

    R = exp(-t / S)                   probabilité de se souvenir du concept
    P = 1 / (1 + exp(-(theta - b)))   probabilité de réussir une question de difficulté b

Les fonctions ne modifient jamais leurs arguments : elles renvoient de nouveaux objets.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime

from src.config import (
    MIN_STABILITY,
    STABILITY_GAIN,
    STABILITY_LOSS,
    THETA_LEARNING_RATE,
)
from src.logic.models import Mastery

SECONDS_PER_DAY = 86400


def success_probability(theta: float, difficulty_value: float) -> float:
    """Probabilité de réussir une question de difficulté `difficulty_value` (modèle logistique)."""
    return 1.0 / (1.0 + math.exp(-(theta - difficulty_value)))


def recall_probability(mastery: Mastery, now: datetime) -> float:
    """Probabilité de se souvenir encore du concept à l'instant `now` (courbe d'oubli).

    Un concept jamais révisé renvoie 0 : il est considéré comme totalement à apprendre.
    """
    if mastery.last_review is None:
        return 0.0
    days = max((now - mastery.last_review).total_seconds() / SECONDS_PER_DAY, 0.0)
    return math.exp(-days / mastery.stability)


def update_mastery(
    mastery: Mastery, correct: bool, difficulty_value: float, now: datetime
) -> Mastery:
    """Renvoie la maîtrise mise à jour après une réponse.

    - le niveau theta monte après une bonne réponse (d'autant plus qu'elle était improbable)
      et baisse après une erreur ;
    - la stabilité est multipliée par 1,8 après une bonne réponse, par 0,5 après une erreur
      (avec un minimum de 0,5 jour) ;
    - la date de dernière révision devient `now`.
    """
    p = success_probability(mastery.theta, difficulty_value)
    y = 1.0 if correct else 0.0
    new_theta = mastery.theta + THETA_LEARNING_RATE * (y - p)
    if correct:
        new_stability = mastery.stability * STABILITY_GAIN
    else:
        new_stability = max(mastery.stability * STABILITY_LOSS, MIN_STABILITY)
    return replace(mastery, theta=new_theta, stability=new_stability, last_review=now)


def mastery_percent(mastery: Mastery) -> float:
    """Niveau affiché à l'étudiant (BF-08) : probabilité, en %, de réussir une question moyenne."""
    return 100.0 * success_probability(mastery.theta, 0.0)
