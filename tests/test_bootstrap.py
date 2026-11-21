"""Tests de l'initialisation et de la banque de questions du chapitre 3 (BF-10, BNF-04)."""

import json
from collections import Counter

import pytest

from src.config import DEFAULT_BANK_PATH, DEFAULT_CHAPTER_TITLE
from src.data import repository
from src.logic import auth, importer
from src.logic.bootstrap import initialize_database

DIFFICULTIES = {"facile", "moyen", "difficile"}


@pytest.fixture
def ready_db(conn, now):
    """Une base initialisée comme à la première exécution de l'application."""
    initialize_database(conn, "admin-pass-1", "demo-pass-1", now=now)
    return conn


# ---------- Initialisation ----------

def test_initialization_creates_accounts_and_question_bank(conn, now):
    """BF-10 : l'initialisation crée l'administrateur, le compte de démonstration et la banque."""
    summary = initialize_database(conn, "admin-pass-1", "demo-pass-1", now=now)
    assert summary.admin_created and summary.demo_created
    assert summary.questions_imported >= 30
    assert summary.chapter_title == DEFAULT_CHAPTER_TITLE


def test_created_accounts_can_log_in_with_the_right_roles(ready_db):
    """BF-02 : l'administrateur et l'étudiant de démonstration se connectent avec leur mot de passe."""
    assert auth.login(ready_db, "admin", "admin-pass-1").is_admin is True
    assert auth.login(ready_db, "demo", "demo-pass-1").is_admin is False


def test_initialization_can_be_run_again_without_duplicates(ready_db, now):
    """BNF-04 : relancer l'initialisation ne recrée ni comptes ni questions."""
    before = repository.list_chapters(ready_db)
    summary = initialize_database(ready_db, "admin-pass-1", "demo-pass-1", now=now)
    assert not summary.admin_created and not summary.demo_created
    assert summary.questions_imported == 0
    assert repository.list_chapters(ready_db) == before


def test_initialization_does_not_overwrite_existing_passwords(ready_db, now):
    """BNF-02 : relancer avec un autre mot de passe ne modifie pas le compte existant."""
    initialize_database(ready_db, "autre-mot-de-passe", "demo-pass-1", now=now)
    assert auth.login(ready_db, "admin", "admin-pass-1").is_admin is True


def test_unreadable_bank_stops_the_initialization_with_a_clear_error(conn, now, tmp_path):
    """BNF-04 : une banque illisible donne une erreur explicite au lieu d'une base incomplète silencieuse."""
    bad_bank = tmp_path / "mauvaise_banque.csv"
    bad_bank.write_text("colonne_inconnue\nvaleur\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="illisible"):
        initialize_database(conn, "admin-pass-1", "demo-pass-1", bank_path=bad_bank, now=now)


# ---------- Qualité de la banque de questions ----------

@pytest.fixture
def bank(ready_db):
    chapter = repository.list_chapters(ready_db)[0]
    return repository.load_questions(ready_db, chapter.id)


def test_bank_files_are_fully_valid():
    """BF-10 : le fichier CSV de la banque ne contient aucune ligne invalide."""
    content = importer.decode_upload(DEFAULT_BANK_PATH.read_bytes())
    rows, errors, file_error = importer.parse_questions(content, "csv")
    assert file_error is None and errors == []
    assert len(rows) >= 30


def test_csv_and_json_banks_contain_the_same_questions():
    """BF-10 : les deux formats fournis décrivent exactement les mêmes questions."""
    csv_rows, _, _ = importer.parse_questions(importer.decode_upload(DEFAULT_BANK_PATH.read_bytes()), "csv")
    json_path = DEFAULT_BANK_PATH.with_suffix(".json")
    json_rows, _, _ = importer.parse_questions(json_path.read_text(encoding="utf-8"), "json")
    assert [row for _, row in csv_rows] == [row for _, row in json_rows]
    assert isinstance(json.loads(json_path.read_text(encoding="utf-8")), list)


def test_bank_covers_several_concepts_with_all_difficulties(bank):
    """BF-06 : chaque concept a des questions de chaque difficulté, pour que l'adaptation ait du choix."""
    concepts = {q.concept for q in bank}
    assert len(concepts) >= 6
    for concept in concepts:
        assert {q.difficulty for q in bank if q.concept == concept} == DIFFICULTIES, concept


def test_bank_is_not_trivially_guessable(bank):
    """BF-04 : la bonne réponse n'est pas toujours à la même place, et aucune place n'est écrasante."""
    positions = Counter(q.correct_index for q in bank)
    assert len(positions) == 4
    assert max(positions.values()) <= 0.4 * len(bank)


def test_bank_questions_are_clean_and_unique(bank):
    """BF-05 : chaque question a 4 options différentes, une explication, et aucune n'est en double."""
    assert len({q.text for q in bank}) == len(bank)
    for q in bank:
        assert len(set(option.lower() for option in q.options)) == 4, q.text
        assert q.explanation.strip(), q.text


def test_bank_explanations_cite_the_course(bank):
    """BF-05 : chaque explication renvoie à la diapositive du cours (l'étudiant sait où réviser)."""
    assert all("Cours, diapo" in q.explanation for q in bank)
