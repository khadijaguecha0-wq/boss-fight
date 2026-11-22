"""Tests du service de jeu : déroulement complet d'un combat avec la base (BF-03 à BF-09, BNF-04)."""

import random
from datetime import timedelta

import pytest

from src.data import repository
from src.logic import game_service
from src.logic.battle import BattleStatus
from src.logic.game_service import GameError


def answer_correctly(conn, session, now):
    return game_service.submit_answer(conn, session, session.current.correct_index, now)


def answer_wrongly(conn, session, now):
    return game_service.submit_answer(conn, session, (session.current.correct_index + 1) % 4, now)


# ---------- Démarrage ----------

def test_cannot_start_a_battle_on_an_empty_chapter(conn, student, now):
    """BF-03 : un chapitre sans question ne peut pas être lancé."""
    empty = repository.get_or_create_chapter(conn, "Chapitre vide")
    with pytest.raises(GameError, match="aucune question"):
        game_service.start_battle(conn, student, empty, now)


def test_cannot_start_a_battle_on_an_unknown_chapter(conn, student, now):
    """BF-03 : un chapitre qui n'existe pas est refusé avec un message clair."""
    with pytest.raises(GameError, match="n'existe pas"):
        game_service.start_battle(conn, student, 999, now)


def test_starting_a_battle_prepares_the_first_question_and_records_it(conn, student, sample_chapter, now):
    """BF-04 : le combat démarre avec un boss plein, 5 vies, une première question, et une ligne en base."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    assert (session.battle.boss_hp, session.battle.lives) == (100, 5)
    assert session.current is not None and session.last_result is None
    assert repository.get_battle(conn, session.battle_id)["status"] == "en_cours"


def test_the_first_question_is_an_easy_one_for_a_new_student(conn, student, sample_chapter, now):
    """BF-06 : un étudiant neuf commence par une question facile (cible theta - 0,85 = -0,85)."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    assert session.current.difficulty == "facile"


def test_chapter_list_comes_from_the_database(conn, sample_chapter):
    """BF-03 : l'écran de choix reçoit chaque chapitre avec son nombre de questions."""
    (chapter,) = game_service.list_chapters(conn)
    assert (chapter.title, chapter.question_count) == ("Chapitre test", 6)


# ---------- Réponses ----------

def test_correct_answer_hurts_the_boss_and_is_saved(conn, student, sample_chapter, now):
    """BF-04, BF-06 : une bonne réponse retire des PV, et la réponse et la maîtrise sont enregistrées."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    question = session.current
    result = answer_correctly(conn, session, now)

    assert result.correct and session.battle.boss_hp == 100 - result.damage
    (stored,) = repository.list_answers(conn, session.battle_id)
    assert (stored["question_id"], stored["is_correct"]) == (question.id, 1)
    assert question.concept in repository.load_masteries(conn, student.id, sample_chapter)


def test_wrong_answer_costs_a_life_and_returns_the_correction(conn, student, sample_chapter, now):
    """BF-04, BF-05 : une erreur coûte une vie, et la correction avec explication est renvoyée."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    result = answer_wrongly(conn, session, now)
    assert not result.correct and session.battle.lives == 4
    assert result.correct_index == session.current.correct_index
    assert result.explanation == "Parce que."
    assert session.last_result is result


def test_cannot_answer_the_same_question_twice(conn, student, sample_chapter, now):
    """BF-06 : une fois la réponse donnée, on ne peut plus répondre à la même question."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    answer_correctly(conn, session, now)
    with pytest.raises(GameError, match="déjà reçu"):
        answer_correctly(conn, session, now)
    assert len(repository.list_answers(conn, session.battle_id)) == 1


def test_invalid_option_is_refused_and_nothing_is_recorded(conn, student, sample_chapter, now):
    """Robustesse : une option inexistante est refusée sans rien modifier."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    with pytest.raises(GameError):
        game_service.submit_answer(conn, session, 9, now)
    assert session.battle.lives == 5 and repository.list_answers(conn, session.battle_id) == []


def test_next_question_requires_an_answer_first(conn, student, sample_chapter, now):
    """BF-05 : on ne passe pas à la suite sans avoir répondu (la correction s'affiche avant)."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(1))
    with pytest.raises(GameError, match="Réponds d'abord"):
        game_service.next_question(conn, session, now)


def test_questions_are_never_repeated_within_a_battle(conn, student, sample_chapter, now):
    """BF-06 : jusqu'à épuisement des questions, aucune n'est posée deux fois."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(7))
    seen = []
    while session.current is not None:
        seen.append(session.current.id)
        answer_wrongly_or_right = answer_correctly if len(seen) % 2 else answer_wrongly
        answer_wrongly_or_right(conn, session, now)
        game_service.next_question(conn, session, now)
    assert len(seen) == len(set(seen))


# ---------- Fin de combat ----------

def test_victory_is_saved_with_score_and_summary(conn, student, now):
    """BF-04, BF-07 : en répondant juste jusqu'au bout, le boss tombe ; la victoire est enregistrée."""
    chapter_id = repository.get_or_create_chapter(conn, "Chapitre assez long")
    for i in range(8):  # 8 questions moyennes = 120 PV de dégâts possibles pour un boss à 100 PV
        repository.add_question(conn, chapter_id, f"Concept {i % 2}", f"Question {i} ?", ("A", "B", "C", "D"), 0, "moyen", "E")
    session = game_service.start_battle(conn, student, chapter_id, now, random.Random(2))
    while session.current is not None:
        answer_correctly(conn, session, now)
        game_service.next_question(conn, session, now)

    summary = session.summary
    assert session.battle.status == BattleStatus.VICTOIRE and session.battle.boss_hp == 0
    assert summary.victory is True and summary.correct_count == summary.answered_count == 7
    stored = repository.get_battle(conn, session.battle_id)
    assert stored["status"] == "victoire" and stored["ended_at"] is not None
    assert (stored["correct_count"], stored["answered_count"]) == (7, 7)


def test_defeat_after_five_mistakes_is_saved(conn, student, sample_chapter, now):
    """BF-04, BF-07 : cinq erreurs terminent le combat par une défaite, enregistrée dès la dernière réponse."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(3))
    for mistake in range(5):
        answer_wrongly(conn, session, now)
        if mistake < 4:
            game_service.next_question(conn, session, now)

    assert session.battle.lives == 0 and session.finished  # sans même appeler next_question
    assert session.summary.victory is False
    assert repository.get_battle(conn, session.battle_id)["status"] == "defaite"
    assert session.summary.weak_concepts, "les concepts ratés doivent être à revoir"
    assert game_service.next_question(conn, session, now) is None


def test_running_out_of_questions_while_the_boss_lives_is_a_defeat(conn, student, now):
    """BF-04 : plus de question et boss en vie : défaite enregistrée."""
    chapter_id = repository.get_or_create_chapter(conn, "Petit chapitre")
    for i in range(2):
        repository.add_question(conn, chapter_id, "Concept", f"Question {i} ?", ("A", "B", "C", "D"), 0, "moyen", "E")
    session = game_service.start_battle(conn, student, chapter_id, now, random.Random(4))
    answer_correctly(conn, session, now)
    game_service.next_question(conn, session, now)
    answer_correctly(conn, session, now)

    assert game_service.next_question(conn, session, now) is None  # 2 x 15 PV : le boss est encore en vie
    assert session.summary.victory is False and session.summary.boss_hp == 70
    assert repository.get_battle(conn, session.battle_id)["status"] == "defaite"


def test_finishing_twice_records_the_battle_only_once(conn, student, sample_chapter, now):
    """BF-09 : demander deux fois le résultat (ex. rechargement de la page) ne duplique rien."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(5))
    for _ in range(5):
        answer_wrongly(conn, session, now)
        game_service.next_question(conn, session, now)
    first = game_service.finish_battle(conn, session, now)
    second = game_service.finish_battle(conn, session, now + timedelta(hours=1))
    assert first is second
    assert len(game_service.progress_points(conn, student)) == 1


def test_cannot_finish_a_battle_that_is_still_running(conn, student, sample_chapter, now):
    """Robustesse : le résumé n'existe qu'une fois le combat terminé."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(5))
    with pytest.raises(GameError, match="pas terminé"):
        game_service.finish_battle(conn, session, now)


# ---------- Maîtrise, tableau de bord, progression ----------

def test_dashboard_marks_untouched_concepts_as_not_evaluated(conn, student, sample_chapter, now):
    """BF-08 : un concept jamais travaillé est signalé « non évalué »."""
    lines = game_service.concept_lines(conn, student, now)
    assert {line.concept for line in lines} == {"Concept A", "Concept B"}
    assert all(line.status == "Non évalué" and line.percent is None for line in lines)


def test_dashboard_shows_level_status_and_retention_after_a_battle(conn, student, sample_chapter, now):
    """BF-08 : après un combat, niveau, statut, date de révision et rétention estimée apparaissent."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(6))
    answer_wrongly(conn, session, now)
    touched = session.current.concept

    lines = {line.concept: line for line in game_service.concept_lines(conn, student, now)}
    line = lines[touched]
    assert line.percent < 60 and line.status == "À revoir"
    assert line.last_review == now
    assert line.retention == pytest.approx(100.0)  # révisé à l'instant : on s'en souvient encore
    other = next(c for c in lines if c != touched)
    assert lines[other].status == "Non évalué"


def test_retention_drops_as_days_go_by(conn, student, sample_chapter, now):
    """BF-06, BNF-08 : plus le temps passe depuis la dernière révision, plus la rétention estimée baisse."""
    session = game_service.start_battle(conn, student, sample_chapter, now, random.Random(6))
    answer_correctly(conn, session, now)
    concept = session.current.concept
    today = {l.concept: l for l in game_service.concept_lines(conn, student, now)}[concept]
    later = {l.concept: l for l in game_service.concept_lines(conn, student, now + timedelta(days=5))}[concept]
    assert later.retention < today.retention


def test_progress_curve_gets_one_point_per_finished_battle(conn, student, sample_chapter, now):
    """BF-09 : un point par combat terminé, dans l'ordre chronologique."""
    for day, seed in enumerate((1, 2)):
        moment = now + timedelta(days=day)
        session = game_service.start_battle(conn, student, sample_chapter, moment, random.Random(seed))
        for _ in range(5):
            answer_wrongly(conn, session, moment)
            game_service.next_question(conn, session, moment)
    points = game_service.progress_points(conn, student)
    assert [p[0] for p in points] == [now, now + timedelta(days=1)]
    assert all(0 < value < 100 for _, value in points)


def test_second_battle_continues_from_saved_mastery(conn, student, sample_chapter, now):
    """BF-06, BNF-04 : le combat suivant reprend la maîtrise enregistrée au lieu de repartir de zéro."""
    first = game_service.start_battle(conn, student, sample_chapter, now, random.Random(8))
    answer_correctly(conn, first, now)
    saved = dict(first.battle.masteries)

    second = game_service.start_battle(conn, student, sample_chapter, now + timedelta(days=1), random.Random(9))
    assert second.battle.masteries == saved
