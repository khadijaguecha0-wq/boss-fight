"""Tests du modèle d'adaptation : courbe d'oubli et niveau (BF-06, BF-08, BNF-08)."""

import math
from datetime import timedelta

import pytest

from src.config import DIFFICULTY_VALUE, MIN_STABILITY
from src.logic.memory_model import (
    mastery_percent,
    recall_probability,
    success_probability,
    update_mastery,
)
from src.logic.models import Mastery


# ---------- Courbe d'oubli ----------

def test_recall_is_one_right_after_review(now):
    """BNF-08 : juste après une révision, la probabilité de rappel vaut 1."""
    m = Mastery(last_review=now)
    assert recall_probability(m, now) == pytest.approx(1.0)


def test_recall_decreases_with_time(now):
    """BNF-08 : la probabilité de rappel décroît avec le temps écoulé."""
    m = Mastery(stability=2.0, last_review=now)
    after_1_day = recall_probability(m, now + timedelta(days=1))
    after_5_days = recall_probability(m, now + timedelta(days=5))
    assert 1.0 > after_1_day > after_5_days > 0.0


def test_recall_matches_formula(now):
    """BNF-08 : R = exp(-t / S), ici t = 2 jours et S = 2 jours."""
    m = Mastery(stability=2.0, last_review=now)
    assert recall_probability(m, now + timedelta(days=2)) == pytest.approx(math.exp(-1))


def test_higher_stability_means_slower_forgetting(now):
    """BNF-08 : à durée égale, un concept plus stable est mieux retenu."""
    later = now + timedelta(days=3)
    fragile = Mastery(stability=1.0, last_review=now)
    solid = Mastery(stability=10.0, last_review=now)
    assert recall_probability(solid, later) > recall_probability(fragile, later)


def test_recall_of_never_reviewed_concept_is_zero(now):
    """BF-06 : un concept jamais révisé est considéré comme totalement à apprendre."""
    assert recall_probability(Mastery(), now) == 0.0


def test_recall_ignores_dates_in_the_future(now):
    """Robustesse : une date de révision dans le futur ne donne jamais plus de 1."""
    m = Mastery(last_review=now + timedelta(days=1))
    assert recall_probability(m, now) == pytest.approx(1.0)


# ---------- Probabilité de réussite ----------

def test_success_probability_is_half_when_level_equals_difficulty():
    """BF-06 : si le niveau égale la difficulté, on a une chance sur deux."""
    assert success_probability(0.7, 0.7) == pytest.approx(0.5)


def test_success_probability_increases_with_level():
    """BF-06 : plus le niveau est élevé, plus la réussite est probable."""
    assert success_probability(2.0, 0.0) > success_probability(0.0, 0.0) > success_probability(-2.0, 0.0)


def test_success_probability_decreases_with_difficulty():
    """BF-06 : plus la question est difficile, moins la réussite est probable."""
    easy = success_probability(0.0, DIFFICULTY_VALUE["facile"])
    hard = success_probability(0.0, DIFFICULTY_VALUE["difficile"])
    assert easy > hard


# ---------- Mise à jour après une réponse ----------

def test_correct_answer_raises_level_and_stability(now):
    """BNF-08 : bonne réponse sur une question moyenne : theta = 0 + 0,4 x (1 - 0,5), S x 1,8."""
    new = update_mastery(Mastery(), correct=True, difficulty_value=0.0, now=now)
    assert new.theta == pytest.approx(0.2)
    assert new.stability == pytest.approx(1.8)


def test_wrong_answer_lowers_level_and_halves_stability(now):
    """BNF-08 : erreur à theta = 1, S = 4 sur une question moyenne."""
    p = 1 / (1 + math.exp(-1))
    new = update_mastery(Mastery(theta=1.0, stability=4.0), correct=False, difficulty_value=0.0, now=now)
    assert new.theta == pytest.approx(1.0 + 0.4 * (0 - p))
    assert new.stability == pytest.approx(2.0)


def test_stability_never_goes_below_minimum(now):
    """BNF-08 : la stabilité ne descend jamais sous le minimum, même après plusieurs erreurs."""
    m = Mastery()
    for _ in range(5):
        m = update_mastery(m, correct=False, difficulty_value=0.0, now=now)
    assert m.stability == pytest.approx(MIN_STABILITY)


def test_update_sets_last_review(now):
    """BF-08 : la date de dernière révision devient la date de la réponse."""
    new = update_mastery(Mastery(), correct=True, difficulty_value=0.0, now=now)
    assert new.last_review == now


def test_update_does_not_modify_the_original(now):
    """Robustesse : l'ancienne maîtrise reste intacte, on reçoit un nouvel objet."""
    old = Mastery()
    update_mastery(old, correct=True, difficulty_value=0.0, now=now)
    assert old == Mastery()


def test_a_surprising_success_teaches_more_than_an_expected_one(now):
    """BF-06 : réussir une question difficile fait plus progresser que réussir une facile."""
    after_hard = update_mastery(Mastery(), True, DIFFICULTY_VALUE["difficile"], now)
    after_easy = update_mastery(Mastery(), True, DIFFICULTY_VALUE["facile"], now)
    assert after_hard.theta > after_easy.theta


def test_repeated_success_makes_forgetting_slower(now):
    """BNF-08 : après plusieurs bonnes réponses, la stabilité a augmenté."""
    m = Mastery()
    for _ in range(3):
        m = update_mastery(m, True, 0.0, now)
    assert m.stability == pytest.approx(1.8 ** 3)


# ---------- Niveau affiché ----------

def test_new_concept_is_displayed_at_fifty_percent():
    """BF-08 : un concept neuf est affiché à 50 % (une chance sur deux)."""
    assert mastery_percent(Mastery()) == pytest.approx(50.0)


def test_displayed_level_grows_with_theta():
    """BF-08 : le pourcentage affiché augmente avec le niveau."""
    assert mastery_percent(Mastery(theta=1.5)) > mastery_percent(Mastery(theta=0.0))
