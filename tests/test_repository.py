"""Tests de la couche données : utilisateurs, chapitres, questions, maîtrise, combats (BF-03, BF-08, BNF-02, BNF-04)."""

import sqlite3
from datetime import timedelta

import pytest

from src.data import repository
from src.logic.battle import BattleStatus
from src.logic.models import Mastery

OPTIONS = ("Option 1", "Option 2", "Option 3", "Option 4")


# ---------- Utilisateurs ----------

def test_create_and_find_a_user(conn, now):
    """BF-01 : un utilisateur créé peut être retrouvé avec son hachage."""
    created = repository.create_user(conn, "alice", "hash-bidon", "etudiant", now)
    user, stored_hash = repository.get_user_with_hash(conn, "alice")
    assert user == created
    assert stored_hash == "hash-bidon"


def test_duplicate_username_is_refused(conn, now):
    """BF-01 : deux comptes ne peuvent pas avoir le même pseudo (même avec une casse différente)."""
    repository.create_user(conn, "alice", "h", "etudiant", now)
    with pytest.raises(repository.UsernameTakenError):
        repository.create_user(conn, "Alice", "h", "etudiant", now)


def test_unknown_username_returns_none(conn):
    """BF-02 : un pseudo inconnu ne renvoie rien."""
    assert repository.get_user_with_hash(conn, "personne") is None


def test_unknown_role_is_refused_by_the_database(conn, now):
    """BNF-02 : la base elle-même refuse un rôle inventé."""
    with pytest.raises(sqlite3.IntegrityError):
        repository.create_user(conn, "alice", "h", "superadmin", now)


def test_sql_injection_attempt_is_harmless(conn, now):
    """BNF-02 : les requêtes sont paramétrées, un pseudo piégé est traité comme un simple texte."""
    evil = "x'; DROP TABLE users; --"
    repository.create_user(conn, evil, "h", "etudiant", now)
    assert repository.get_user_with_hash(conn, evil) is not None
    assert repository.get_user_with_hash(conn, "' OR '1'='1") is None
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1  # la table existe toujours


# ---------- Chapitres et questions ----------

def test_chapter_list_shows_question_counts(conn, sample_chapter):
    """BF-03 : chaque chapitre est listé avec son nombre de questions, même s'il est vide."""
    empty_id = repository.get_or_create_chapter(conn, "Chapitre vide")
    chapters = {c.title: c for c in repository.list_chapters(conn)}
    assert chapters["Chapitre test"].question_count == 6
    assert chapters["Chapitre vide"].question_count == 0
    assert chapters["Chapitre vide"].id == empty_id


def test_get_or_create_chapter_does_not_duplicate(conn):
    """BF-10 : demander deux fois le même chapitre ne le crée qu'une fois."""
    first = repository.get_or_create_chapter(conn, "Chapitre 1")
    second = repository.get_or_create_chapter(conn, "Chapitre 1")
    assert first == second
    assert len(repository.list_chapters(conn)) == 1


def test_question_round_trip(conn):
    """BF-04 : une question enregistrée est rechargée à l'identique (options, bonne réponse, concept)."""
    chapter_id = repository.get_or_create_chapter(conn, "Chapitre 1")
    question_id = repository.add_question(
        conn, chapter_id, "MoSCoW", "Que signifie M ?", ("Must", "Maybe", "Medium", "Most"), 0,
        "facile", "M = Must have.",
    )
    (loaded,) = repository.load_questions(conn, chapter_id)
    assert loaded.id == question_id
    assert loaded.text == "Que signifie M ?"
    assert loaded.options == ("Must", "Maybe", "Medium", "Most")
    assert loaded.correct_index == 0
    assert loaded.concept == "MoSCoW"
    assert loaded.difficulty == "facile"
    assert loaded.explanation == "M = Must have."


def test_load_questions_only_returns_the_requested_chapter(conn, sample_chapter):
    """BF-03 : on ne charge que les questions du chapitre choisi."""
    other = repository.get_or_create_chapter(conn, "Autre chapitre")
    repository.add_question(conn, other, "X", "Question ?", OPTIONS, 1, "moyen", "Expl.")
    assert len(repository.load_questions(conn, sample_chapter)) == 6
    assert len(repository.load_questions(conn, other)) == 1


def test_duplicate_question_is_refused(conn, sample_chapter):
    """BF-10 : la même question pour le même concept ne peut pas être ajoutée deux fois."""
    with pytest.raises(repository.DuplicateQuestionError):
        repository.add_question(
            conn, sample_chapter, "Concept A", "Concept A : question facile ?", OPTIONS, 0, "facile", "Expl.",
        )
    assert len(repository.load_questions(conn, sample_chapter)) == 6


def test_same_concept_name_in_two_chapters_is_two_concepts(conn):
    """Modèle de données : un concept appartient à un chapitre, deux chapitres peuvent réutiliser un nom."""
    one = repository.get_or_create_chapter(conn, "Chapitre 1")
    two = repository.get_or_create_chapter(conn, "Chapitre 2")
    repository.add_question(conn, one, "UML", "Q ?", OPTIONS, 0, "facile", "E")
    repository.add_question(conn, two, "UML", "Q ?", OPTIONS, 0, "facile", "E")
    assert conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == 2


def test_invalid_data_is_refused_by_the_database_without_leftovers(conn):
    """BNF-04 : une question invalide est refusée par la base et ne laisse pas de concept orphelin."""
    chapter_id = repository.get_or_create_chapter(conn, "Chapitre 1")
    with pytest.raises(sqlite3.IntegrityError):
        repository.add_question(conn, chapter_id, "Concept", "Q ?", OPTIONS, 0, "impossible", "E")
    with pytest.raises(sqlite3.IntegrityError):
        repository.add_question(conn, chapter_id, "Concept", "Q ?", OPTIONS, 7, "facile", "E")
    assert conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0] == 0


# ---------- Maîtrise des concepts ----------

def test_never_reviewed_student_has_no_saved_mastery(conn, student, sample_chapter):
    """BF-08 : tant qu'il n'a rien révisé, aucune maîtrise n'est enregistrée."""
    assert repository.load_masteries(conn, student.id, sample_chapter) == {}


def test_mastery_round_trip(conn, student, sample_chapter, now):
    """BNF-04 : niveau, stabilité et date de révision sont retrouvés exactement."""
    saved = Mastery(theta=0.6, stability=3.24, last_review=now)
    repository.save_mastery(conn, student.id, sample_chapter, "Concept A", saved)
    assert repository.load_masteries(conn, student.id, sample_chapter) == {"Concept A": saved}


def test_saving_mastery_again_updates_the_same_row(conn, student, sample_chapter, now):
    """BF-06 : après chaque réponse, la maîtrise est mise à jour (pas dupliquée)."""
    repository.save_mastery(conn, student.id, sample_chapter, "Concept A", Mastery(0.1, 1.8, now))
    later = now + timedelta(days=1)
    repository.save_mastery(conn, student.id, sample_chapter, "Concept A", Mastery(0.5, 3.2, later))
    loaded = repository.load_masteries(conn, student.id, sample_chapter)
    assert loaded == {"Concept A": Mastery(0.5, 3.2, later)}
    assert conn.execute("SELECT COUNT(*) FROM mastery").fetchone()[0] == 1


def test_mastery_without_review_date_is_kept_as_none(conn, student, sample_chapter):
    """BF-08 : un concept jamais révisé garde une date vide."""
    repository.save_mastery(conn, student.id, sample_chapter, "Concept B", Mastery())
    assert repository.load_masteries(conn, student.id, sample_chapter)["Concept B"].last_review is None


def test_saving_mastery_for_unknown_concept_fails(conn, student, sample_chapter):
    """Robustesse : on ne peut pas enregistrer la maîtrise d'un concept qui n'existe pas."""
    with pytest.raises(LookupError):
        repository.save_mastery(conn, student.id, sample_chapter, "Inconnu", Mastery())


def test_masteries_belong_to_one_student(conn, student, admin, sample_chapter, now):
    """BF-02 : la progression d'un étudiant n'est jamais visible par un autre."""
    repository.save_mastery(conn, student.id, sample_chapter, "Concept A", Mastery(1.0, 5.0, now))
    assert repository.load_masteries(conn, admin.id, sample_chapter) == {}


def test_dashboard_rows_list_every_concept_of_the_student(conn, student, sample_chapter, now):
    """BF-08 : le tableau de bord reçoit une ligne par concept travaillé, avec son chapitre."""
    repository.save_mastery(conn, student.id, sample_chapter, "Concept A", Mastery(0.2, 1.8, now))
    repository.save_mastery(conn, student.id, sample_chapter, "Concept B", Mastery(-0.3, 0.9, now))
    rows = repository.list_mastery_rows(conn, student.id)
    assert [(r.chapter_title, r.concept) for r in rows] == [
        ("Chapitre test", "Concept A"),
        ("Chapitre test", "Concept B"),
    ]
    assert rows[0].mastery.theta == pytest.approx(0.2)


# ---------- Combats et réponses ----------

def test_battle_lifecycle_is_recorded(conn, student, sample_chapter, now):
    """BF-07 : le début, les réponses et la fin d'un combat sont enregistrés."""
    question_ids = [q.id for q in repository.load_questions(conn, sample_chapter)]
    battle_id = repository.start_battle(conn, student.id, sample_chapter, now)
    assert repository.get_battle(conn, battle_id)["status"] == "en_cours"

    repository.record_answer(conn, battle_id, question_ids[0], 2, True, now)
    repository.record_answer(conn, battle_id, question_ids[1], 0, False, now)
    repository.finish_battle(conn, battle_id, BattleStatus.VICTOIRE, 0, 4, 1, 2, 72.5, now)

    battle = repository.get_battle(conn, battle_id)
    assert battle["status"] == "victoire"
    assert (battle["boss_hp"], battle["lives"]) == (0, 4)
    assert (battle["correct_count"], battle["answered_count"]) == (1, 2)
    answers = repository.list_answers(conn, battle_id)
    assert [(a["question_id"], a["chosen_index"], a["is_correct"]) for a in answers] == [
        (question_ids[0], 2, 1),
        (question_ids[1], 0, 0),
    ]


def test_defeat_status_is_stored_without_accent(conn, student, sample_chapter, now):
    """BF-07 : l'état « défaite » est enregistré sous la forme « defaite » acceptée par la base."""
    battle_id = repository.start_battle(conn, student.id, sample_chapter, now)
    repository.finish_battle(conn, battle_id, BattleStatus.DEFAITE, 60, 0, 3, 8, 41.0, now)
    assert repository.get_battle(conn, battle_id)["status"] == "defaite"


def test_progress_history_lists_finished_battles_in_order(conn, student, sample_chapter, now):
    """BF-09 : la courbe de progression reçoit la maîtrise moyenne de chaque combat terminé, dans l'ordre."""
    second = repository.start_battle(conn, student.id, sample_chapter, now + timedelta(days=2))
    first = repository.start_battle(conn, student.id, sample_chapter, now)
    repository.start_battle(conn, student.id, sample_chapter, now + timedelta(days=5))  # jamais terminé
    repository.finish_battle(conn, second, BattleStatus.VICTOIRE, 0, 3, 7, 8, 68.0, now + timedelta(days=2))
    repository.finish_battle(conn, first, BattleStatus.DEFAITE, 40, 0, 3, 8, 52.0, now)
    history = repository.mastery_history(conn, student.id)
    assert history == [(now, 52.0), (now + timedelta(days=2), 68.0)]


def test_foreign_keys_are_enforced(conn, now):
    """Intégrité : on ne peut pas enregistrer une réponse pour un combat qui n'existe pas."""
    with pytest.raises(sqlite3.IntegrityError):
        repository.record_answer(conn, battle_id=999, question_id=1, chosen_index=0, is_correct=True, now=now)


# ---------- Fiabilité ----------

def test_progress_survives_an_application_restart(tmp_path, now):
    """BNF-04 : après fermeture puis réouverture du fichier de base, rien n'est perdu."""
    db_file = tmp_path / "boss_fight.db"
    first = repository.connect(db_file)
    repository.init_db(first)
    user = repository.create_user(first, "alice", "h", "etudiant", now)
    chapter_id = repository.get_or_create_chapter(first, "Chapitre 1")
    repository.add_question(first, chapter_id, "MoSCoW", "Q ?", OPTIONS, 3, "moyen", "E")
    saved = Mastery(theta=0.8, stability=5.832, last_review=now)
    repository.save_mastery(first, user.id, chapter_id, "MoSCoW", saved)
    first.close()  # l'application s'arrête

    second = repository.connect(db_file)  # elle redémarre
    assert repository.load_masteries(second, user.id, chapter_id) == {"MoSCoW": saved}
    assert len(repository.load_questions(second, chapter_id)) == 1
    second.close()


def test_init_db_can_be_run_twice(conn, sample_chapter):
    """BNF-04 : relancer la création des tables ne détruit aucune donnée."""
    repository.init_db(conn)
    assert len(repository.load_questions(conn, sample_chapter)) == 6
