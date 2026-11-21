"""Outils partagés par tous les tests."""

from datetime import datetime

import pytest

from src.logic.models import Question

NOW = datetime(2026, 11, 21, 12, 0, 0)


@pytest.fixture
def now():
    """Une date fixe, pour que les tests donnent toujours le même résultat."""
    return NOW


@pytest.fixture
def make_question():
    """Fabrique une question de test : make_question(id=3, concept="INVEST", difficulty="facile")."""

    def _make(id=1, concept="MoSCoW", difficulty="moyen", correct_index=0):
        return Question(
            id=id,
            text=f"Question {id}",
            options=("A", "B", "C", "D"),
            correct_index=correct_index,
            concept=concept,
            difficulty=difficulty,
            explanation="Parce que.",
        )

    return _make
