"""Tests des objets métier (Question, Mastery)."""

import pytest

from src.config import INITIAL_STABILITY, INITIAL_THETA
from src.logic.models import Mastery, Question


def test_question_is_correct(make_question):
    """BF-04 : la bonne option est reconnue, les autres non."""
    q = make_question(correct_index=2)
    assert q.is_correct(2) is True
    assert q.is_correct(0) is False


def test_question_rejects_unknown_difficulty():
    """BF-10 : une difficulté inconnue est refusée."""
    with pytest.raises(ValueError):
        Question(1, "?", ("A", "B", "C", "D"), 0, "MoSCoW", "impossible")


def test_question_rejects_out_of_range_answer():
    """BF-10 : l'indice de la bonne réponse doit désigner une option existante."""
    with pytest.raises(ValueError):
        Question(1, "?", ("A", "B", "C", "D"), 4, "MoSCoW", "moyen")


def test_default_mastery_is_a_blank_concept():
    """BF-08 : un concept jamais révisé démarre au niveau initial, sans date."""
    m = Mastery()
    assert m.theta == INITIAL_THETA
    assert m.stability == INITIAL_STABILITY
    assert m.last_review is None
