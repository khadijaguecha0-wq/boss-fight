"""Simulation : l'ordre adaptatif fait-il mieux retenir qu'un ordre aléatoire ? (BNF-08)

Lancement :  python -m tools.simulation
Options   :  --students 1000   nombre d'élèves simulés par scénario
             --seed 2026       graine du hasard (mêmes chiffres à chaque lancement)
             --out docs/simulation_resultats.md
             --figure docs/simulation_figure.png   (nécessite matplotlib ; ignoré s'il est absent)

Principe
--------
Chaque élève simulé révise le chapitre pendant 5 séances, avec le MÊME nombre de questions par séance,
puis passe un examen blanc de toutes les questions de la banque. On compare deux façons de choisir les questions :
  - aléatoire : questions tirées au hasard dans la banque ;
  - adaptatif : le vrai code de l'application (`choose_question` et `update_mastery`).

L'élève simulé a une mémoire « cachée » que l'application ne connaît pas : elle ne voit que ses réponses.
Le score à l'examen est calculé à partir de cette mémoire cachée, jamais à partir de l'estimation de l'application.
Les deux méthodes sont comparées sur les mêmes élèves et avec le même hasard pour les réponses (comparaison appariée).

Limite essentielle : c'est un modèle, pas de vrais étudiants. Il vérifie que le choix des questions est cohérent
avec une mémoire qui oublie ; il ne prouve pas l'efficacité sur de vrais élèves.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from src.config import (
    DEFAULT_BANK_PATH,
    DIFFICULTY_VALUE,
    MIN_STABILITY,
    STABILITY_GAIN,
    STABILITY_LOSS,
    THETA_LEARNING_RATE,
    WEAK_THRESHOLD,
)
from src.logic import importer
from src.logic.memory_model import update_mastery
from src.logic.models import Mastery, Question
from src.logic.selector import choose_question

GUESS_RATE = 0.25            # 4 options : un élève qui ne sait rien répond juste une fois sur quatre
LECTURE_DAY = -5.0           # le cours a été suivi 5 jours avant la première séance
BASE_DATE = datetime(2026, 1, 1)
SMALL_EFFECT = 1.0           # un écart de moins d'un point sur 100 est considéré comme très faible
RANDOM = "aléatoire"
ADAPTIVE = "adaptatif"


@dataclass(frozen=True)
class Protocol:
    """Déroulement de l'expérience : jours de révision, jour de l'examen, questions par séance."""

    study_days: tuple = (0, 1, 3, 6, 10)
    exam_day: int = 14
    questions_per_session: int = 12


@dataclass(frozen=True)
class Scenario:
    """Façon dont la mémoire cachée de l'élève fonctionne."""

    key: str
    title: str
    description: str
    ability_mean: float          # niveau moyen de départ (échelle logistique)
    stability_median: float      # stabilité de départ typique, en jours
    stability_spread: float      # dispersion (écart-type du logarithme) de la stabilité de départ
    gain_right: tuple            # multiplication de la stabilité après une bonne réponse (min, max)
    gain_wrong: tuple            # multiplication de la stabilité après une erreur (min, max)
    ability_rule: str            # "fixed" : le niveau monte un peu à chaque réponse ; "logistic" : règle de l'application
    ability_step: tuple = (0.10, 0.30)


SCENARIOS = {
    "A": Scenario(
        "A", "Mémoire différente du modèle",
        "Cas principal. La mémoire cachée n'obéit pas aux mêmes constantes que l'application : oubli plus lent "
        "ou plus rapide selon l'élève, et une erreur suivie de l'explication fait quand même progresser la mémoire "
        "(l'application, elle, la pénalise).",
        ability_mean=-0.3, stability_median=2.0, stability_spread=0.4,
        gain_right=(1.4, 2.4), gain_wrong=(1.1, 1.5), ability_rule="fixed",
    ),
    "B": Scenario(
        "B", "Mémoire qui suit les règles de l'application",
        "La mémoire cachée suit exactement les règles de mise à jour de l'application (stabilité ×1,8 après une réussite, "
        "×0,5 après une erreur, niveau mis à jour par la même formule). Valeurs de départ identiques à celles du scénario A : "
        "A et B ne diffèrent que par les règles de mise à jour.",
        ability_mean=-0.3, stability_median=2.0, stability_spread=0.4,
        gain_right=(1.8, 1.8), gain_wrong=(0.5, 0.5), ability_rule="logistic",
    ),
    "C": Scenario(
        "C", "Règles de l'application, élèves forts",
        "Comme B, mais les élèves connaissent déjà bien le cours au départ (niveau moyen +2 au lieu de -0,3). "
        "Sert à vérifier que l'absence d'écart en B ne vient pas seulement d'élèves trop faibles.",
        ability_mean=2.0, stability_median=2.0, stability_spread=0.4,
        gain_right=(1.8, 1.8), gain_wrong=(0.5, 0.5), ability_rule="logistic",
    ),
}


# ---------- Banque de questions ----------

def load_bank(path: Path | str = DEFAULT_BANK_PATH) -> list:
    """Charge la banque de questions du chapitre (même fichier et même lecture que l'application)."""
    content = importer.decode_upload(Path(path).read_bytes())
    rows, errors, file_error = importer.parse_questions(content, "csv")
    if file_error or errors:
        raise ValueError(f"Banque illisible : {file_error or errors[0]}")
    return [
        Question(i, row.text, row.options, row.correct_index, row.concept, row.difficulty, row.explanation)
        for i, (_, row) in enumerate(rows, start=1)
    ]


# ---------- Élève simulé ----------

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class HiddenStudent:
    """Mémoire cachée d'un élève simulé : niveau, stabilité et dernière révision de chaque concept."""

    def __init__(self, scenario: Scenario, concepts: list, rng: random.Random) -> None:
        self.rule = scenario.ability_rule
        general = rng.gauss(scenario.ability_mean, 0.5)
        self.ability = {c: rng.gauss(general, 0.7) for c in concepts}
        self.stability = {
            c: scenario.stability_median * math.exp(rng.gauss(0.0, scenario.stability_spread)) for c in concepts
        }
        self.last_day = {c: LECTURE_DAY for c in concepts}
        self.gain_right = rng.uniform(*scenario.gain_right)
        self.gain_wrong = rng.uniform(*scenario.gain_wrong)
        self.step = rng.uniform(*scenario.ability_step)

    def success_probability(self, concept: str, difficulty_value: float, day: float) -> float:
        """Chance de répondre juste : hasard + (1 - hasard) × souvenir × niveau face à la difficulté."""
        recall = math.exp(-max(day - self.last_day[concept], 0.0) / self.stability[concept])
        return GUESS_RATE + (1.0 - GUESS_RATE) * recall * _sigmoid(self.ability[concept] - difficulty_value)

    def answer(self, question: Question, day: float, draw: float) -> bool:
        """Répond (selon le tirage `draw` entre 0 et 1), puis apprend de la réponse et de son explication."""
        b = DIFFICULTY_VALUE[question.difficulty]
        concept = question.concept
        correct = draw < self.success_probability(concept, b, day)
        if self.rule == "logistic":
            self.ability[concept] += THETA_LEARNING_RATE * ((1.0 if correct else 0.0) - _sigmoid(self.ability[concept] - b))
        else:
            self.ability[concept] += self.step
        gain = self.gain_right if correct else self.gain_wrong
        self.stability[concept] = max(self.stability[concept] * gain, MIN_STABILITY)
        self.last_day[concept] = day
        return correct

    def exam(self, bank: list, day: float) -> tuple:
        """Score attendu à l'examen blanc (en %) et nombre de concepts sous le seuil « à revoir »."""
        per_concept: dict = {}
        total = 0.0
        for q in bank:
            p = self.success_probability(q.concept, DIFFICULTY_VALUE[q.difficulty], day)
            total += p
            per_concept.setdefault(q.concept, []).append(p)
        weak = sum(1 for values in per_concept.values() if 100.0 * sum(values) / len(values) < WEAK_THRESHOLD)
        return 100.0 * total / len(bank), weak


# ---------- Une expérience ----------

def run_strategy(strategy: str, student: HiddenStudent, bank: list, protocol: Protocol,
                 noise: random.Random, select: random.Random) -> tuple:
    """Fait réviser l'élève selon la stratégie, puis renvoie son résultat à l'examen."""
    masteries: dict = {}
    for day in protocol.study_days:
        now = BASE_DATE + timedelta(days=day)
        asked: set = set()
        for _ in range(protocol.questions_per_session):
            if strategy == ADAPTIVE:
                question = choose_question(bank, masteries, asked, now=now, rng=select)
            else:
                question = select.choice([q for q in bank if q.id not in asked])
            asked.add(question.id)
            correct = student.answer(question, day, noise.random())
            if strategy == ADAPTIVE:
                current = masteries.get(question.concept, Mastery())
                masteries[question.concept] = update_mastery(
                    current, correct, DIFFICULTY_VALUE[question.difficulty], now
                )
    return student.exam(bank, protocol.exam_day)


@dataclass
class ScenarioResult:
    """Chiffres d'un scénario, sur l'ensemble des élèves simulés."""

    scenario: Scenario
    protocol: Protocol
    students: int
    none_scores: list
    random_scores: list
    adaptive_scores: list
    random_weak: list
    adaptive_weak: list

    @property
    def differences(self) -> list:
        """Différence de score élève par élève : adaptatif moins aléatoire."""
        return [a - r for a, r in zip(self.adaptive_scores, self.random_scores)]

    def mean_ci(self, values: list) -> tuple:
        """Moyenne et intervalle de confiance à 95 % (approximation normale)."""
        mean = statistics.fmean(values)
        half = 1.96 * statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0
        return mean, mean - half, mean + half

    @property
    def share_better(self) -> float:
        """Part des élèves pour qui l'ordre adaptatif donne un meilleur score que l'ordre aléatoire (en %)."""
        diffs = self.differences
        return 100.0 * sum(1 for d in diffs if d > 0) / len(diffs)


def run_scenario(scenario: Scenario, students: int, seed: int, protocol: Protocol | None = None,
                 bank: list | None = None) -> ScenarioResult:
    """Simule `students` élèves : chacun révise une fois en aléatoire et une fois en adaptatif."""
    protocol = protocol or Protocol()
    bank = bank or load_bank()
    concepts = sorted({q.concept for q in bank})
    result = ScenarioResult(scenario, protocol, students, [], [], [], [], [])

    for i in range(students):
        label = f"{seed}/{scenario.key}/{i}"
        reference = HiddenStudent(scenario, concepts, random.Random(f"{label}/student"))
        result.none_scores.append(reference.exam(bank, protocol.exam_day)[0])
        for strategy in (RANDOM, ADAPTIVE):
            student = HiddenStudent(scenario, concepts, random.Random(f"{label}/student"))  # même élève
            noise = random.Random(f"{label}/noise")                                       # mêmes tirages
            select = random.Random(f"{label}/select/{strategy}")
            score, weak = run_strategy(strategy, student, bank, protocol, noise, select)
            if strategy == RANDOM:
                result.random_scores.append(score)
                result.random_weak.append(weak)
            else:
                result.adaptive_scores.append(score)
                result.adaptive_weak.append(weak)
    return result


# ---------- Présentation ----------

def verdict(result: ScenarioResult) -> str:
    """Phrase de lecture, déduite des chiffres (jamais écrite d'avance)."""
    mean, low, high = result.mean_ci(result.differences)
    if low > 0 and mean < SMALL_EFFECT:
        return (f"L'ordre adaptatif donne un meilleur score attendu, mais l'écart est très faible : +{mean:.1f} point "
                f"(intervalle à 95 % : de {low:.1f} à {high:.1f}).")
    if low > 0:
        return (f"L'ordre adaptatif donne un meilleur score attendu : +{mean:.1f} points "
                f"(intervalle à 95 % : de {low:.1f} à {high:.1f}).")
    if high < 0:
        return (f"L'ordre adaptatif donne un moins bon score attendu : {mean:.1f} points "
                f"(intervalle à 95 % : de {low:.1f} à {high:.1f}).")
    return (f"Pas de différence nette entre les deux ordres : {mean:+.1f} points "
            f"(intervalle à 95 % : de {low:.1f} à {high:.1f}, il contient 0).")


def build_markdown(main: list, sensitivity: list, students: int, seed: int) -> str:
    """Rapport de simulation au format Markdown."""
    protocol = main[0].protocol
    lines = [
        "# Simulation : ordre adaptatif contre ordre aléatoire (BNF-08)",
        "",
        "Rapport généré par `python -m tools.simulation` (voir le haut du fichier `tools/simulation.py`).",
        f"Élèves simulés par scénario : {students}. Graine du hasard : {seed} (mêmes chiffres à chaque lancement).",
        "",
        "## Question posée",
        "",
        "Pour un même nombre de questions posées, choisir les questions avec le modèle de l'application "
        "(courbe d'oubli + niveau par concept) fait-il mieux retenir qu'un tirage au hasard ?",
        "",
        "## Méthode",
        "",
        f"- Chaque élève simulé révise pendant {len(protocol.study_days)} séances (jours {', '.join(map(str, protocol.study_days))}), "
        f"avec {protocol.questions_per_session} questions par séance, dans les deux cas.",
        f"- Le cours a été suivi {int(-LECTURE_DAY)} jours avant la première séance. L'examen blanc a lieu le jour {protocol.exam_day} "
        "et reprend toutes les questions de la banque (35 questions, 8 concepts, la vraie banque de l'application).",
        "- Ordre aléatoire : les questions sont tirées au hasard, sans répétition dans une séance.",
        "- Ordre adaptatif : le vrai code de l'application (`choose_question` et `update_mastery`).",
        f"- La mémoire de l'élève est cachée : l'application ne voit que ses réponses. La probabilité de répondre juste vaut "
        f"{GUESS_RATE:.2f} + {1 - GUESS_RATE:.2f} × souvenir × niveau (4 options : on peut deviner).",
        "- Le score à l'examen est le score attendu calculé avec la mémoire cachée, jamais avec l'estimation de l'application.",
        "- Comparaison appariée : le même élève, avec la même suite de nombres aléatoires pour ses réponses, révise une fois dans chaque ordre.",
        "- « Sans révision » : le même élève passe l'examen sans avoir révisé (point de référence).",
        "",
        "## Résultats",
        "",
    ]
    for r in main:
        n_mean, _, _ = r.mean_ci(r.none_scores)
        r_mean, r_low, r_high = r.mean_ci(r.random_scores)
        a_mean, a_low, a_high = r.mean_ci(r.adaptive_scores)
        d_mean, d_low, d_high = r.mean_ci(r.differences)
        lines += [
            f"### Scénario {r.scenario.key} : {r.scenario.title}",
            "",
            r.scenario.description,
            "",
            "| Stratégie | Score attendu à l'examen (%) | Intervalle à 95 % | Concepts sous 60 % à l'examen |",
            "|---|---|---|---|",
            f"| Sans révision | {n_mean:.1f} | - | - |",
            f"| Ordre aléatoire | {r_mean:.1f} | {r_low:.1f} à {r_high:.1f} | {statistics.fmean(r.random_weak):.2f} sur 8 |",
            f"| Ordre adaptatif | {a_mean:.1f} | {a_low:.1f} à {a_high:.1f} | {statistics.fmean(r.adaptive_weak):.2f} sur 8 |",
            "",
            f"Écart adaptatif moins aléatoire : {d_mean:+.2f} points (intervalle à 95 % : {d_low:+.2f} à {d_high:+.2f}). "
            f"L'ordre adaptatif est meilleur pour {r.share_better:.0f} % des élèves.",
            "",
            verdict(r),
            "",
        ]
    break_even = math.log(1 / STABILITY_LOSS) / (math.log(STABILITY_GAIN) + math.log(1 / STABILITY_LOSS))
    lines += [
        "### Remarque sur les constantes du modèle",
        "",
        f"Avec une stabilité multipliée par {STABILITY_GAIN} après une réussite et par {STABILITY_LOSS} après une erreur, "
        f"la stabilité d'un concept n'augmente en moyenne que si le taux de réussite dépasse {100 * break_even:.0f} %. "
        "Les scénarios B et C, où la mémoire cachée suit ces règles, sont cohérents avec cette propriété : "
        "les élèves y retiennent peu à 14 jours quel que soit l'ordre des questions. Ce lien n'est pas démontré ici.",
        "",
    ]
    lines += [
        "## Sensibilité (scénario A)",
        "",
        "Écart de score attendu (adaptatif moins aléatoire, en points) quand on change le protocole :",
        "",
        "| Questions par séance | Examen au jour | Aléatoire (%) | Adaptatif (%) | Écart (points) | Intervalle à 95 % |",
        "|---|---|---|---|---|---|",
    ]
    for r in sensitivity:
        r_mean = statistics.fmean(r.random_scores)
        a_mean = statistics.fmean(r.adaptive_scores)
        d_mean, d_low, d_high = r.mean_ci(r.differences)
        lines.append(
            f"| {r.protocol.questions_per_session} | {r.protocol.exam_day} | {r_mean:.1f} | {a_mean:.1f} | "
            f"{d_mean:+.2f} | {d_low:+.2f} à {d_high:+.2f} |"
        )
    lines += [
        "",
        "## Limites (à écrire dans le rapport)",
        "",
        "- C'est une simulation : les élèves sont des modèles mathématiques. Elle montre que le choix des questions est cohérent "
        "avec une mémoire qui oublie, pas qu'il améliore les résultats de vrais étudiants. Seule une expérience avec de vrais "
        "étudiants pourrait le démontrer.",
        "- Les résultats dépendent des hypothèses du simulateur (oubli exponentiel, valeurs des paramètres cachés). "
        "Le scénario A les écarte volontairement de celles de l'application ; les scénarios B et C les reprennent.",
        "- La banque est petite (35 questions) : une même question revient d'une séance à l'autre.",
        "- Le protocole (5 séances, 12 questions par séance, examen au jour 14) et le scénario A ont été fixés avant le premier lancement "
        "et n'ont jamais été modifiés pour améliorer leur résultat. Une première version du scénario B (stabilité de départ de 1 jour "
        "pour tous) donnait un monde où personne ne retient rien (environ 32 % à l'examen dans les deux ordres, écart nul) : ses valeurs "
        "de départ ont été alignées sur celles de A. Le scénario C a été ajouté ensuite ; des essais exploratoires "
        "de 300 élèves, avec un niveau de départ moyen de +1, +2 et +3, n'avaient pas montré d'écart net.",
        "",
    ]
    return "\n".join(lines)


def save_figure(main: list, path: Path) -> bool:
    """Dessine la figure du rapport si matplotlib est installé. Renvoie False sinon."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    surface, ink, muted = "#fcfcfb", "#0b0b0b", "#52514e"
    orange, blue = "#eb6834", "#2a78d6"          # couleurs validées (écart CVD, contraste)

    def fr(value: float, digits: int = 1) -> str:
        """Nombre avec une virgule décimale, comme en français."""
        return f"{value:.{digits}f}".replace(".", ",")

    figure, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.4), facecolor=surface)
    for ax in (left, right):
        ax.set_facecolor(surface)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(muted)
        ax.tick_params(colors=muted, labelsize=9)
        ax.yaxis.grid(True, color="#e4e3df", linewidth=0.8)
        ax.set_axisbelow(True)

    # Panneau de gauche : score attendu à l'examen, par scénario
    width = 0.34
    for k, (label, color, attr) in enumerate((("Ordre aléatoire", orange, "random_scores"),
                                              ("Ordre adaptatif", blue, "adaptive_scores"))):
        xs, means, errors = [], [], []
        for i, r in enumerate(main):
            mean, low, high = r.mean_ci(getattr(r, attr))
            xs.append(i + (k - 0.5) * (width + 0.02))
            means.append(mean)
            errors.append(high - mean)
        left.bar(xs, means, width, yerr=errors, color=color, label=label,
                 error_kw={"ecolor": ink, "elinewidth": 1, "capsize": 3})
    chance = statistics.fmean(main[0].none_scores)
    left.axhline(chance, color=muted, linestyle="--", linewidth=1.2, label=f"Sans révision ({fr(chance, 0)} % : hasard)")
    for i, r in enumerate(main):
        d_mean = r.mean_ci(r.differences)[0]
        top = max(statistics.fmean(r.random_scores), statistics.fmean(r.adaptive_scores))
        left.text(i, top + 5, f"{d_mean:+.1f} point".replace(".", ",") + ("s" if abs(d_mean) >= 1.5 else ""),
                  ha="center", fontsize=9, color=ink, fontweight="bold")
    left.set_xticks(range(len(main)), [f"Scénario {r.scenario.key}" for r in main])
    left.set_ylim(0, 100)
    left.set_ylabel("Score attendu à l'examen (%)", color=muted, fontsize=9)
    left.set_title("Score à l'examen blanc (jour 14)", fontsize=11, color=ink, loc="left")
    left.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=muted)

    # Panneau de droite : écart par élève dans le scénario A
    first = main[0]
    right.hist(first.differences, bins=30, color=blue, edgecolor=surface, linewidth=0.8)
    right.axvline(0, color=ink, linewidth=1)
    mean = first.mean_ci(first.differences)[0]
    right.axvline(mean, color=orange, linewidth=1.6, linestyle="--")
    right.text(mean + 0.2, right.get_ylim()[1] * 0.93, f"moyenne {fr(mean)} points", color=ink, fontsize=8.5)
    right.set_xlabel("Score adaptatif moins score aléatoire (points)", color=muted, fontsize=9)
    right.set_ylabel("Nombre d'élèves simulés", color=muted, fontsize=9)
    right.set_title(f"Écart élève par élève, scénario {first.scenario.key}", fontsize=11, color=ink, loc="left")
    figure.tight_layout()
    figure.savefig(path, dpi=200, facecolor=surface)
    plt.close(figure)
    return True


def main() -> None:
    """Lance les scénarios, écrit le rapport Markdown et, si possible, la figure."""
    parser = argparse.ArgumentParser(description="Simulation ordre adaptatif contre ordre aléatoire.")
    parser.add_argument("--students", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", default="docs/simulation_resultats.md")
    parser.add_argument("--figure", default="docs/simulation_figure.png")
    args = parser.parse_args()

    bank = load_bank()
    main_results = [run_scenario(s, args.students, args.seed, bank=bank) for s in SCENARIOS.values()]
    grid = [
        Protocol(questions_per_session=q, exam_day=d) for q in (8, 12, 20) for d in (7, 14, 28)
    ]
    sensitivity = [run_scenario(SCENARIOS["A"], args.students, args.seed, protocol=p, bank=bank) for p in grid]

    report = build_markdown(main_results, sensitivity, args.students, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Rapport écrit dans {out}")
    for r in main_results:
        print(f"  Scénario {r.scenario.key} : {verdict(r)}")
    if args.figure:
        print("Figure écrite" if save_figure(main_results, Path(args.figure)) else "matplotlib absent : figure ignorée")


if __name__ == "__main__":
    main()
