"""Démo en console du moteur de jeu (sans base de données ni interface web).

Lancement :  python demo_console.py

Sert à voir l'adaptation fonctionner avant d'avoir l'interface : les questions
ci-dessous sont provisoires, la vraie banque de questions viendra à l'étape 5.
"""

from __future__ import annotations

import random
import sys

from src.logic.battle import Battle, BattleStatus
from src.logic.memory_model import mastery_percent
from src.logic.models import Question
from src.logic.selector import choose_question

LETTERS = "ABCD"

SAMPLE_QUESTIONS = [
    Question(1, "Que signifie le « M » de MoSCoW ?",
             ("Must have", "Maybe", "Medium", "Most wanted"), 0, "MoSCoW", "facile",
             "M = Must have : ce qui est indispensable à cette version."),
    Question(2, "Dans MoSCoW, quelle catégorie regroupe ce qu'on exclut volontairement de la version en cours ?",
             ("Must have", "Should have", "Could have", "Won't have"), 3, "MoSCoW", "moyen",
             "Won't have : exclu pour cette version, mais pas forcément abandonné pour toujours."),
    Question(3, "Une fonctionnalité importante, mais dont l'absence laisse la solution viable, est classée :",
             ("Must have", "Should have", "Could have", "Won't have"), 1, "MoSCoW", "difficile",
             "Should have : importante mais pas vitale ; la solution reste utilisable sans elle."),
    Question(4, "Que signifie le « I » de INVEST ?",
             ("Independent", "Interesting", "Iterative", "Integrated"), 0, "INVEST", "facile",
             "Independent : une user story doit pouvoir être réalisée indépendamment des autres."),
    Question(5, "Une user story « Testable » est une story qui :",
             ("est écrite en langage technique", "possède des critères d'acceptation vérifiables",
              "est testée uniquement par le développeur", "n'a pas besoin de test"), 1, "INVEST", "moyen",
             "Testable : on peut vérifier objectivement qu'elle est réalisée grâce à ses critères d'acceptation."),
    Question(6, "Que signifie « Negotiable » dans INVEST ?",
             ("Le prix de la story est négociable", "Les détails se discutent entre l'équipe et le client",
              "La story ne peut jamais changer", "Le client doit l'accepter sans discussion"), 1, "INVEST", "difficile",
             "Negotiable : la story est un point de départ de discussion, pas un contrat figé."),
    Question(7, "Lequel de ces besoins est fonctionnel ?",
             ("L'étudiant peut créer un compte", "Le site répond en moins de 1 seconde",
              "Les mots de passe sont chiffrés", "L'application est disponible 24 h sur 24"), 0,
             "Besoins fonctionnels et non fonctionnels", "facile",
             "Un besoin fonctionnel décrit ce que le système fait ; les autres décrivent comment il doit le faire."),
    Question(8, "« Le temps de réponse doit rester inférieur à 1 seconde » est un besoin :",
             ("fonctionnel", "non fonctionnel (performance)", "un cas d'utilisation", "une tâche du planning"), 1,
             "Besoins fonctionnels et non fonctionnels", "moyen",
             "Il décrit une qualité du système (performance), pas une fonctionnalité."),
    Question(9, "Quelle exigence non fonctionnelle est correctement formulée ?",
             ("L'application doit être rapide", "L'application doit être agréable à utiliser",
              "95 % des requêtes répondent en moins de 1 seconde", "L'application doit être fiable"), 2,
             "Besoins fonctionnels et non fonctionnels", "difficile",
             "Une bonne exigence non fonctionnelle est mesurable : ici, un seuil chiffré vérifiable."),
]


def hp_bar(hp: int, width: int = 20) -> str:
    """Barre de vie du boss en texte."""
    filled = round(width * hp / 100)
    return "█" * filled + "░" * (width - filled)


def ask_choice(n_options: int):
    """Demande une lettre à l'étudiant. Renvoie l'indice choisi, ou None si l'entrée est fermée."""
    while True:
        try:
            raw = input("Ta réponse : ").strip().upper()
        except EOFError:
            return None
        if raw in LETTERS[:n_options]:
            return LETTERS.index(raw)
        print(f"Tape une lettre entre A et {LETTERS[n_options - 1]}.")


def main() -> None:
    """Joue un combat complet dans le terminal."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # évite un plantage si le terminal ne sait pas afficher █ ou ♥
    rng = random.Random()
    battle = Battle()
    print("=== BOSS FIGHT (démo console) ===")

    while not battle.is_over():
        question = choose_question(SAMPLE_QUESTIONS, battle.masteries, battle.asked_ids, rng=rng)
        if question is None:
            battle.mark_questions_exhausted()
            break

        print(f"\nBoss : {hp_bar(battle.boss_hp)} {battle.boss_hp}/100     Vies : {'♥' * battle.lives}")
        print(f"[{question.concept} · {question.difficulty}]  {question.text}")
        for letter, option in zip(LETTERS, question.options):
            print(f"  {letter}. {option}")

        choice = ask_choice(len(question.options))
        if choice is None:
            print("\nEntrée fermée, fin de la démo.")
            return

        result = battle.apply_answer(question, choice)
        if result.correct:
            print(f"✔ Bonne réponse ! Le boss perd {result.damage} PV.")
        else:
            print(f"✘ Mauvaise réponse, tu perds 1 vie. La bonne réponse était {LETTERS[result.correct_index]}.")
        print(f"  {result.explanation}")
        print(f"  Maîtrise de « {result.concept} » : {mastery_percent(result.new_mastery):.0f} %")

    print("\n=== " + ("VICTOIRE !" if battle.status == BattleStatus.VICTOIRE else "DÉFAITE") + " ===")
    print(f"Score : {battle.correct_count} bonne(s) réponse(s) sur {battle.answered_count}")
    weak = battle.weak_concepts()
    if weak:
        print("À revoir :")
        for concept, percent in weak:
            print(f"  - {concept} ({percent:.0f} %)")


if __name__ == "__main__":
    main()
