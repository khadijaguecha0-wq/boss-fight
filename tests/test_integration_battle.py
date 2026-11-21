"""Tests d'intégration : un combat complet joué avec les vraies questions et la vraie base (BF-04 à BF-08)."""

import random
import time
from datetime import timedelta

import pytest

from src.data import repository
from src.logic import auth
from src.logic.battle import Battle, BattleStatus
from src.logic.bootstrap import initialize_database
from src.logic.memory_model import mastery_percent
from src.logic.selector import choose_question


def play_battle(conn, user, chapter, now, rng, answer_correctly=True):
    """Joue un combat entier en enregistrant tout, comme le fera l'interface."""
    questions = repository.load_questions(conn, chapter.id)
    battle = Battle(masteries=repository.load_masteries(conn, user.id, chapter.id))
    battle_id = repository.start_battle(conn, user.id, chapter.id, now)

    while not battle.is_over():
        question = choose_question(questions, battle.masteries, battle.asked_ids, now=now, rng=rng)
        if question is None:
            battle.mark_questions_exhausted()
            break
        choice = question.correct_index if answer_correctly else (question.correct_index + 1) % 4
        result = battle.apply_answer(question, choice, now)
        repository.record_answer(conn, battle_id, question.id, choice, result.correct, now)
        repository.save_mastery(conn, user.id, chapter.id, question.concept, result.new_mastery)

    mean = sum(mastery_percent(m) for m in battle.masteries.values()) / max(len(battle.masteries), 1)
    repository.finish_battle(
        conn, battle_id, battle.status, battle.boss_hp, battle.lives,
        battle.correct_count, battle.answered_count, mean, now,
    )
    return battle, battle_id


@pytest.fixture
def world(conn, now):
    """Base initialisée, étudiant de démonstration connecté et premier chapitre."""
    initialize_database(conn, "admin-pass-1", "demo-pass-1", now=now)
    user = auth.login(conn, "demo", "demo-pass-1")
    return conn, user, repository.list_chapters(conn)[0]


def test_a_perfect_player_wins_and_everything_is_saved(world, now):
    """BF-04, BF-06, BNF-04 : victoire, réponses, maîtrise et historique sont enregistrés en base."""
    conn, user, chapter = world
    battle, battle_id = play_battle(conn, user, chapter, now, random.Random(1))

    assert battle.status == BattleStatus.VICTOIRE and battle.boss_hp == 0
    stored = repository.get_battle(conn, battle_id)
    assert stored["status"] == "victoire"
    assert stored["answered_count"] == len(repository.list_answers(conn, battle_id)) == battle.answered_count
    assert repository.load_masteries(conn, user.id, chapter.id) == battle.masteries
    assert len(repository.mastery_history(conn, user.id)) == 1


def test_a_player_who_always_fails_loses_after_five_mistakes(world, now):
    """BF-04 : cinq mauvaises réponses font perdre le combat, le boss garde tous ses PV."""
    conn, user, chapter = world
    battle, battle_id = play_battle(conn, user, chapter, now, random.Random(2), answer_correctly=False)

    assert battle.status == BattleStatus.DEFAITE
    assert (battle.answered_count, battle.lives, battle.boss_hp) == (5, 0, 100)
    assert repository.get_battle(conn, battle_id)["status"] == "defaite"
    assert battle.weak_concepts(), "les concepts ratés doivent être signalés à revoir"


def test_no_question_is_asked_twice_in_a_battle(world, now):
    """BF-06 : dans un même combat, une question n'est jamais reposée."""
    conn, user, chapter = world
    _, battle_id = play_battle(conn, user, chapter, now, random.Random(3))
    asked = [a["question_id"] for a in repository.list_answers(conn, battle_id)]
    assert len(asked) == len(set(asked))


def test_second_battle_starts_from_the_saved_mastery(world, now):
    """BF-06, BF-08 : le combat suivant reprend la maîtrise enregistrée, l'étudiant ne repart pas de zéro."""
    conn, user, chapter = world
    first, _ = play_battle(conn, user, chapter, now, random.Random(4))

    second, _ = play_battle(conn, user, chapter, now + timedelta(days=3), random.Random(5))
    for concept, before in first.masteries.items():
        if concept in second.masteries:
            assert second.masteries[concept].stability >= before.stability
    assert len(repository.mastery_history(conn, user.id)) == 2


def test_one_students_progress_does_not_leak_to_another(world, now):
    """BF-02 : l'administrateur ne voit pas la progression de l'étudiant (données personnelles)."""
    conn, user, chapter = world
    play_battle(conn, user, chapter, now, random.Random(6))
    admin_user = auth.login(conn, "admin", "admin-pass-1")
    assert repository.load_masteries(conn, admin_user.id, chapter.id) == {}


def test_next_question_is_fast_with_1000_questions(conn, now):
    """BNF-01 : avec 1000 questions en base, 95 % des « question suivante » prennent moins de 1 seconde.

    Mesure sur la logique et la base (chargement, choix, mise à jour), sans l'affichage Streamlit.
    """
    chapter_id = repository.get_or_create_chapter(conn, "Gros chapitre")
    difficulties = ["facile", "moyen", "difficile"]
    for i in range(1000):
        repository.add_question(
            conn, chapter_id, f"Concept {i % 20}", f"Question {i} ?",
            ("A", "B", "C", "D"), i % 4, difficulties[i % 3], "Parce que.",
        )

    start = time.perf_counter()
    questions = repository.load_questions(conn, chapter_id)
    loading_time = time.perf_counter() - start
    assert len(questions) == 1000 and loading_time < 1.0

    battle = Battle(boss_hp=10**6, lives=10**6)  # un combat très long, pour enchaîner 100 questions
    durations = []
    for _ in range(100):
        start = time.perf_counter()
        question = choose_question(questions, battle.masteries, battle.asked_ids, now=now)
        battle.apply_answer(question, question.correct_index, now)
        durations.append(time.perf_counter() - start)
    assert sorted(durations)[94] < 1.0
