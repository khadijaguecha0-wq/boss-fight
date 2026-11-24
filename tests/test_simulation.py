"""Tests de la simulation « ordre adaptatif contre ordre aléatoire » (BNF-08)."""

import random

import pytest

from tools import simulation
from tools.simulation import (
    ADAPTIVE,
    RANDOM,
    SCENARIOS,
    HiddenStudent,
    Protocol,
    ScenarioResult,
    load_bank,
    run_scenario,
    run_strategy,
)


@pytest.fixture(scope="module")
def bank():
    """La vraie banque de questions de l'application, lue une seule fois."""
    return load_bank()


def make_student(bank, key="A", seed="s"):
    concepts = sorted({q.concept for q in bank})
    return HiddenStudent(SCENARIOS[key], concepts, random.Random(seed))


def test_simulation_uses_the_real_question_bank(bank):
    """BNF-08 : la simulation travaille sur les 35 questions et les 8 concepts de la banque de l'application."""
    assert len(bank) == 35
    assert len({q.concept for q in bank}) == 8


def test_same_seed_gives_exactly_the_same_results(bank):
    """BNF-08 : avec la même graine, la simulation redonne exactement les mêmes chiffres (résultats reproductibles)."""
    first = run_scenario(SCENARIOS["A"], 15, seed=1, bank=bank)
    second = run_scenario(SCENARIOS["A"], 15, seed=1, bank=bank)
    assert first.random_scores == second.random_scores
    assert first.adaptive_scores == second.adaptive_scores


def test_both_orders_ask_the_same_number_of_questions_without_repeats_in_a_session(bank, monkeypatch):
    """BNF-08 : comparaison équitable : même nombre de questions pour les deux ordres, sans répétition dans une séance."""
    protocol = Protocol(study_days=(0, 2, 5), questions_per_session=9)
    for strategy in (RANDOM, ADAPTIVE):
        asked = []
        original = HiddenStudent.answer

        def spy(self, question, day, draw, _asked=asked, _original=original):
            _asked.append((day, question.id))
            return _original(self, question, day, draw)

        monkeypatch.setattr(HiddenStudent, "answer", spy)
        run_strategy(strategy, make_student(bank), bank, protocol, random.Random(1), random.Random(2))
        monkeypatch.setattr(HiddenStudent, "answer", original)

        assert len(asked) == 3 * 9
        for day in protocol.study_days:
            ids = [question_id for d, question_id in asked if d == day]
            assert len(ids) == len(set(ids)) == 9


def test_adaptive_order_calls_the_applications_own_selector(bank, monkeypatch):
    """BNF-08 : l'ordre adaptatif simulé utilise le vrai `choose_question` de l'application ; l'ordre aléatoire ne l'utilise pas."""
    calls = []
    real = simulation.choose_question

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(simulation, "choose_question", spy)
    protocol = Protocol(study_days=(0, 1), questions_per_session=5)
    run_strategy(RANDOM, make_student(bank), bank, protocol, random.Random(1), random.Random(2))
    assert calls == []
    run_strategy(ADAPTIVE, make_student(bank), bank, protocol, random.Random(1), random.Random(2))
    assert len(calls) == 2 * 5


def test_exam_score_comes_from_the_hidden_memory_and_is_chance_level_without_review(bank):
    """BNF-08 : sans aucune révision, tout est oublié à l'examen : le score attendu est celui du hasard (25 % pour 4 options)."""
    student = make_student(bank)
    score, weak = student.exam(bank, day=14)
    assert 25.0 <= score < 26.0
    assert weak == 8


def test_reviewing_raises_the_hidden_memory(bank):
    """BNF-08 : réviser un concept juste avant l'examen augmente le score attendu, tout rattrapage oublié reste proche du hasard."""
    student = make_student(bank)
    before, _ = student.exam(bank, day=14)
    for question in [q for q in bank if q.concept == bank[0].concept]:
        student.answer(question, day=13, draw=0.0)  # réponse juste garantie
    after, _ = student.exam(bank, day=14)
    assert after > before


def test_adaptive_order_beats_random_order_in_the_main_scenario(bank):
    """BNF-08 : dans le scénario principal (mémoire différente du modèle), l'ordre adaptatif donne un meilleur score attendu."""
    result = run_scenario(SCENARIOS["A"], 120, seed=2026, bank=bank)
    low = result.mean_ci(result.differences)[1]
    assert low > 0, "l'intervalle à 95 % de l'écart adaptatif - aléatoire devrait être au-dessus de 0"
    assert result.share_better > 60


def make_result(differences):
    """Un résultat de simulation fabriqué à la main, pour tester le texte de conclusion."""
    random_scores = [50.0] * len(differences)
    adaptive_scores = [50.0 + d for d in differences]
    return ScenarioResult(SCENARIOS["A"], Protocol(), len(differences),
                          [25.0] * len(differences), random_scores, adaptive_scores, [3] * len(differences), [3] * len(differences))


def test_conclusion_text_follows_the_numbers_not_the_other_way_round():
    """BNF-08 : le texte de conclusion est déduit des chiffres : meilleur, très faible, sans différence nette ou moins bon."""
    wording = {
        "meilleur": [3.0 + 0.1 * (i % 3) for i in range(60)],
        "très faible": [0.5 + 0.01 * (i % 3) for i in range(60)],
        "Pas de différence nette": [(-1) ** i * 1.0 for i in range(60)],
        "moins bon": [-2.0 - 0.1 * (i % 3) for i in range(60)],
    }
    for expected, differences in wording.items():
        assert expected in simulation.verdict(make_result(differences))


def test_report_states_its_limits_and_the_scenarios(bank):
    """BNF-08 : le rapport généré annonce ses limites (simulation, pas de vrais étudiants) et présente chaque scénario."""
    main = [run_scenario(s, 10, seed=3, bank=bank) for s in SCENARIOS.values()]
    sensitivity = [run_scenario(SCENARIOS["A"], 10, seed=3, protocol=Protocol(questions_per_session=8), bank=bank)]
    report = simulation.build_markdown(main, sensitivity, 10, 3)
    assert "## Limites" in report
    assert "vrais étudiants" in report
    for key in SCENARIOS:
        assert f"Scénario {key}" in report
