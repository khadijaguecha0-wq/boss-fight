"""Choix de la prochaine question selon le niveau et le risque d'oubli (BF-06).

Deux étapes :
1. choisir un concept au hasard, avec une probabilité proportionnelle à son risque d'oubli (1 - R) ;
2. dans ce concept, prendre la question dont la difficulté est la plus proche de
   theta - 0,85, ce qui vise environ 70 % de réussite.
"""

from __future__ import annotations

import random
from datetime import datetime

from src.config import DIFFICULTY_VALUE, MIN_WEIGHT, TARGET_OFFSET
from src.logic.memory_model import recall_probability
from src.logic.models import Mastery, Question


def concept_weights(concepts: list, masteries: dict, now: datetime) -> list:
    """Poids de tirage de chaque concept : son risque d'oubli, avec un minimum de 0,05.

    Un concept jamais révisé a le poids maximal (1,0).
    """
    weights = []
    for concept in concepts:
        mastery = masteries.get(concept, Mastery())
        risk = 1.0 - recall_probability(mastery, now)
        weights.append(max(risk, MIN_WEIGHT))
    return weights


def choose_concept(
    concepts: list, masteries: dict, now: datetime, rng: random.Random
) -> str:
    """Tire un concept au hasard, pondéré par le risque d'oubli."""
    weights = concept_weights(concepts, masteries, now)
    return rng.choices(concepts, weights=weights, k=1)[0]


def choose_question(
    questions: list,
    masteries: dict,
    asked_ids: set,
    now: datetime | None = None,
    rng: random.Random | None = None,
) -> Question | None:
    """Renvoie la prochaine question, ou None s'il n'en reste plus à poser."""
    now = now or datetime.now()
    rng = rng or random.Random()

    candidates = [q for q in questions if q.id not in asked_ids]
    if not candidates:
        return None

    concepts = sorted({q.concept for q in candidates})
    concept = choose_concept(concepts, masteries, now, rng)

    theta = masteries.get(concept, Mastery()).theta
    target = theta - TARGET_OFFSET

    in_concept = [q for q in candidates if q.concept == concept]
    distances = {q.id: abs(DIFFICULTY_VALUE[q.difficulty] - target) for q in in_concept}
    best = min(distances.values())
    closest = [q for q in in_concept if distances[q.id] <= best + 1e-9]
    return rng.choice(closest)
