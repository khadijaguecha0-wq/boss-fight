"""Outils partagés par tous les tests."""

from datetime import datetime

import pytest

from src.data import repository
from src.logic import auth
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


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    """Réduit le nombre de tours PBKDF2 pendant les tests pour qu'ils restent rapides."""
    monkeypatch.setattr(auth, "PBKDF2_ITERATIONS", 1000)


@pytest.fixture
def conn():
    """Une base SQLite vide, en mémoire, avec toutes les tables."""
    connection = repository.connect(":memory:")
    repository.init_db(connection)
    yield connection
    connection.close()


@pytest.fixture
def student(conn, now):
    """Un étudiant déjà inscrit."""
    return auth.register(conn, "alice", "motdepasse1", now=now)


@pytest.fixture
def admin(conn, now):
    """Un administrateur déjà inscrit."""
    return auth.register(conn, "chef", "motdepasse1", role="admin", now=now)


@pytest.fixture
def sample_chapter(conn):
    """Un chapitre de test avec 6 questions : 2 concepts x 3 difficultés. Renvoie l'id du chapitre."""
    chapter_id = repository.get_or_create_chapter(conn, "Chapitre test")
    for concept in ("Concept A", "Concept B"):
        for difficulty in ("facile", "moyen", "difficile"):
            repository.add_question(
                conn, chapter_id, concept, f"{concept} : question {difficulty} ?",
                ("Option 1", "Option 2", "Option 3", "Option 4"), 2, difficulty, "Parce que.",
            )
    return chapter_id
