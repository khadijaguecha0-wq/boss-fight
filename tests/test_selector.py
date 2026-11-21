"""Tests du choix de la prochaine question (BF-06)."""

import random
from datetime import timedelta

import pytest

from src.logic.models import Mastery
from src.logic.selector import choose_concept, choose_question, concept_weights


def test_no_question_left_returns_none(make_question):
    """BF-04 : sans question disponible, le sélecteur renvoie None."""
    q = make_question(id=1)
    assert choose_question([q], {}, asked_ids={1}) is None
    assert choose_question([], {}, asked_ids=set()) is None


def test_asked_questions_are_never_chosen(make_question, now):
    """BF-06 : on ne repose jamais une question déjà posée."""
    questions = [make_question(id=i) for i in range(1, 6)]
    asked = {1, 2, 3, 4}
    for seed in range(20):
        q = choose_question(questions, {}, asked, now=now, rng=random.Random(seed))
        assert q.id == 5


def test_never_reviewed_concept_has_maximal_weight_and_fresh_one_minimal(now):
    """BF-06 : jamais vu = poids 1 ; revu à l'instant avec grande stabilité = poids minimal."""
    masteries = {"B": Mastery(stability=10.0, last_review=now)}
    weights = concept_weights(["A", "B"], masteries, now)
    assert weights == pytest.approx([1.0, 0.05])


def test_weight_grows_as_time_passes(now):
    """BF-06 : plus on attend, plus le risque d'oubli (et donc le poids) augmente."""
    masteries = {"A": Mastery(stability=2.0, last_review=now)}
    soon = concept_weights(["A"], masteries, now + timedelta(days=1))[0]
    later = concept_weights(["A"], masteries, now + timedelta(days=6))[0]
    assert later > soon


def test_weights_are_never_zero(now):
    """BF-06 : même un concept parfaitement retenu garde une petite chance d'être tiré."""
    masteries = {"A": Mastery(stability=1000.0, last_review=now)}
    assert concept_weights(["A"], masteries, now)[0] > 0.0


def test_concept_at_risk_is_chosen_much_more_often(now):
    """BF-06 : le concept en train d'être oublié est tiré beaucoup plus souvent."""
    masteries = {
        "oublie": Mastery(stability=1.0, last_review=now - timedelta(days=10)),
        "frais": Mastery(stability=10.0, last_review=now),
    }
    rng = random.Random(42)
    draws = [choose_concept(["frais", "oublie"], masteries, now, rng) for _ in range(500)]
    assert draws.count("oublie") > 450


@pytest.mark.parametrize(
    "theta, expected_difficulty",
    [(0.0, "facile"), (1.0, "moyen"), (2.0, "difficile")],
)
def test_difficulty_follows_the_student_level(make_question, now, theta, expected_difficulty):
    """BF-06 : plus le niveau est haut, plus la question choisie est difficile (cible theta - 0,85)."""
    questions = [
        make_question(id=1, difficulty="facile"),
        make_question(id=2, difficulty="moyen"),
        make_question(id=3, difficulty="difficile"),
    ]
    masteries = {"MoSCoW": Mastery(theta=theta)}
    q = choose_question(questions, masteries, set(), now=now, rng=random.Random(0))
    assert q.difficulty == expected_difficulty


def test_same_seed_gives_same_choice(make_question, now):
    """Reproductibilité : avec la même graine aléatoire, le choix est identique."""
    questions = [make_question(id=i, concept=c) for i, c in enumerate("ABCDEF", start=1)]
    first = choose_question(questions, {}, set(), now=now, rng=random.Random(7))
    second = choose_question(questions, {}, set(), now=now, rng=random.Random(7))
    assert first == second


def test_works_without_explicit_date_and_random_generator(make_question):
    """Utilisation normale : sans date ni générateur fournis, une question est renvoyée."""
    questions = [make_question(id=1), make_question(id=2)]
    assert choose_question(questions, {}, set()) in questions
