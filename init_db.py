"""Crée la base de données prête à l'emploi : tables, comptes et banque de questions.

Lancement :  python init_db.py

Peut être relancé sans danger (rien n'est dupliqué). Pour choisir le mot de passe de
l'administrateur, définis la variable d'environnement BOSS_FIGHT_ADMIN_PASSWORD avant de lancer.
"""

import os

from src.config import (
    ADMIN_USERNAME,
    DB_PATH,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_DEMO_PASSWORD,
    DEMO_USERNAME,
)
from src.data import repository
from src.logic.bootstrap import initialize_database


def main() -> None:
    """Initialise la base et affiche ce qui a été créé."""
    admin_password = os.environ.get("BOSS_FIGHT_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    conn = repository.connect()
    summary = initialize_database(conn, admin_password, DEFAULT_DEMO_PASSWORD)

    print(f"Base de données : {DB_PATH}")
    print(f"  compte administrateur « {ADMIN_USERNAME} » : {'créé' if summary.admin_created else 'déjà présent'}")
    print(f"  compte de démonstration « {DEMO_USERNAME} » : {'créé' if summary.demo_created else 'déjà présent'}")
    if summary.chapter_title:
        print(f"  {summary.questions_imported} questions importées dans « {summary.chapter_title} »")
    else:
        print("  banque de questions : déjà présente")
    for chapter in repository.list_chapters(conn):
        print(f"  - {chapter.title} : {chapter.question_count} questions")
    if "BOSS_FIGHT_ADMIN_PASSWORD" not in os.environ:
        print("Attention : mot de passe administrateur de DÉMONSTRATION. "
              "Définis BOSS_FIGHT_ADMIN_PASSWORD pour en choisir un autre.")
    conn.close()


if __name__ == "__main__":
    main()
