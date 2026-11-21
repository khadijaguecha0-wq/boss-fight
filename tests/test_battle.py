"""Tests des règles du combat (BF-04 à BF-07)."""

import pytest

from src.logic.battle import Battle, BattleStatus
from src.logic.models import Mastery


def test_new_battle_starts_with_full_boss_and_five_lives():
    """BF-04 : le boss démarre à 100 PV et le joueur à 5 vies."""
    b = Battle()
    assert b.boss_hp == 100
    assert b.lives == 5
    assert b.status == BattleStatus.EN_COURS
    assert not b.is_over()


@pytest.mark.parametrize("difficulty, expected_damage", [("facile", 10), ("moyen", 15), ("difficile", 20)])
def test_correct_answer_damages_boss_by_difficulty(make_question, now, difficulty, expected_damage):
    """BF-04 : une bonne réponse retire 10, 15 ou 20 PV selon la difficulté."""
    b = Battle()
    result = b.apply_answer(make_question(difficulty=difficulty), choice=0, now=now)
    assert result.correct is True
    assert result.damage == expected_damage
    assert b.boss_hp == 100 - expected_damage
    assert b.lives == 5


def test_wrong_answer_costs_one_life_and_spares_the_boss(make_question, now):
    """BF-04 : une mauvaise réponse retire 1 vie et le boss ne perd rien."""
    b = Battle()
    result = b.apply_answer(make_question(), choice=1, now=now)
    assert result.correct is False
    assert result.lives_lost == 1
    assert b.lives == 4
    assert b.boss_hp == 100


def test_result_contains_the_correction_and_explanation(make_question, now):
    """BF-05 : après une réponse, on connaît la bonne option et l'explication."""
    b = Battle()
    result = b.apply_answer(make_question(correct_index=2), choice=0, now=now)
    assert result.correct_index == 2
    assert result.explanation == "Parce que."


def test_victory_when_boss_reaches_zero_and_hp_never_negative(make_question, now):
    """BF-04 : le boss tombe à 0 PV (sans passer sous 0) et le combat est gagné."""
    b = Battle()
    for i in range(1, 8):  # 7 bonnes réponses moyennes : 6 x 15 = 90, puis les 10 PV restants
        b.apply_answer(make_question(id=i), choice=0, now=now)
    assert b.boss_hp == 0
    assert b.status == BattleStatus.VICTOIRE
    assert b.is_over()


def test_last_blow_only_removes_remaining_hp(make_question, now):
    """BF-04 : le dernier coup indique les PV réellement retirés, pas les dégâts théoriques."""
    b = Battle(boss_hp=10)
    result = b.apply_answer(make_question(difficulty="difficile"), choice=0, now=now)
    assert result.damage == 10
    assert b.boss_hp == 0


def test_defeat_when_no_lives_left(make_question, now):
    """BF-04 : à 0 vie, le combat est perdu."""
    b = Battle()
    for i in range(1, 6):
        b.apply_answer(make_question(id=i), choice=3, now=now)
    assert b.lives == 0
    assert b.status == BattleStatus.DEFAITE
    assert b.boss_hp == 100


def test_cannot_answer_once_the_battle_is_over(make_question, now):
    """BF-04 : on ne peut plus répondre après la fin du combat."""
    b = Battle(lives=1)
    b.apply_answer(make_question(id=1), choice=3, now=now)
    with pytest.raises(ValueError):
        b.apply_answer(make_question(id=2), choice=0, now=now)


def test_a_question_is_never_asked_twice(make_question, now):
    """BF-06 : une même question ne peut pas être posée deux fois dans un combat."""
    b = Battle()
    q = make_question(id=1)
    b.apply_answer(q, choice=0, now=now)
    with pytest.raises(ValueError):
        b.apply_answer(q, choice=0, now=now)


@pytest.mark.parametrize("bad_choice", [-1, 4, 99])
def test_invalid_option_is_rejected(make_question, now, bad_choice):
    """Robustesse : une option qui n'existe pas est refusée et ne change rien."""
    b = Battle()
    with pytest.raises(ValueError):
        b.apply_answer(make_question(), choice=bad_choice, now=now)
    assert b.lives == 5 and b.boss_hp == 100 and b.answered_count == 0


def test_answer_updates_the_mastery_of_the_concept(make_question, now):
    """BF-06 : niveau, stabilité et date de révision du concept sont mis à jour."""
    b = Battle()
    result = b.apply_answer(make_question(concept="INVEST"), choice=0, now=now)
    m = b.masteries["INVEST"]
    assert m.theta == pytest.approx(0.2)
    assert m.stability == pytest.approx(1.8)
    assert m.last_review == now
    assert result.new_mastery == m


def test_existing_mastery_is_used_as_starting_point(make_question, now):
    """BF-06 : la maîtrise déjà connue de l'étudiant sert de point de départ."""
    b = Battle(masteries={"MoSCoW": Mastery(theta=1.0, stability=5.0)})
    b.apply_answer(make_question(concept="MoSCoW"), choice=0, now=now)
    assert b.masteries["MoSCoW"].stability == pytest.approx(9.0)


def test_score_counts_correct_and_total_answers(make_question, now):
    """BF-07 : le score est le nombre de bonnes réponses sur le total."""
    b = Battle()
    b.apply_answer(make_question(id=1), choice=0, now=now)
    b.apply_answer(make_question(id=2), choice=1, now=now)
    b.apply_answer(make_question(id=3), choice=0, now=now)
    assert (b.correct_count, b.answered_count) == (2, 3)


def test_running_out_of_questions_is_a_defeat_if_boss_alive():
    """BF-04 : plus de question et boss en vie : défaite."""
    b = Battle()
    b.mark_questions_exhausted()
    assert b.status == BattleStatus.DEFAITE


def test_running_out_of_questions_keeps_a_victory(make_question, now):
    """BF-04 : un combat déjà gagné reste gagné."""
    b = Battle(boss_hp=10)
    b.apply_answer(make_question(), choice=0, now=now)
    b.mark_questions_exhausted()
    assert b.status == BattleStatus.VICTOIRE


def test_weak_concepts_lists_concepts_below_sixty_percent(make_question, now):
    """BF-07 : une erreur laisse le concept sous 60 %, il est signalé à revoir."""
    b = Battle()
    b.apply_answer(make_question(id=1, concept="MoSCoW"), choice=1, now=now)
    weak = b.weak_concepts()
    assert [name for name, _ in weak] == ["MoSCoW"]
    assert weak[0][1] < 60.0


def test_a_well_mastered_concept_is_not_listed(make_question, now):
    """BF-07 : après plusieurs bonnes réponses, le concept n'est plus à revoir."""
    b = Battle()
    for i in range(1, 5):
        b.apply_answer(make_question(id=i, concept="INVEST"), choice=0, now=now)
    assert b.weak_concepts() == []


def test_weak_concepts_are_sorted_from_weakest(make_question, now):
    """BF-07 : la liste commence par le concept le plus faible."""
    b = Battle()
    b.apply_answer(make_question(id=1, concept="A"), choice=0, now=now)  # juste, niveau 55 %
    b.apply_answer(make_question(id=2, concept="B"), choice=1, now=now)  # faux, niveau plus bas
    names = [name for name, _ in b.weak_concepts()]
    assert names == ["B", "A"]
