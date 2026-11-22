"""Point d'entrée de Boss Fight.  Lancement :  streamlit run app.py

Ce fichier ne contient que l'aiguillage entre les écrans : les règles du jeu sont dans
`src/logic/` et l'accès à la base dans `src/data/`.
"""

import os
from contextlib import closing

import streamlit as st

from src.config import DEFAULT_ADMIN_PASSWORD, DEFAULT_DEMO_PASSWORD
from src.data import repository
from src.logic.bootstrap import initialize_database
from src.ui import (
    auth_page,
    battle_page,
    dashboard_page,
    import_page,
    progress_page,
    result_page,
    sidebar,
    state,
)

PAGES = {
    state.AUTH: auth_page.render,
    state.DASHBOARD: dashboard_page.render,
    state.BATTLE_PAGE: battle_page.render,
    state.RESULT: result_page.render,
    state.PROGRESS: progress_page.render,
    state.IMPORT: import_page.render,
}


@st.cache_resource
def prepare_database() -> bool:
    """Crée la base, les comptes de démonstration et la banque de questions (une seule fois par démarrage)."""
    admin_password = os.environ.get("BOSS_FIGHT_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    with closing(repository.connect()) as conn:
        initialize_database(conn, admin_password, DEFAULT_DEMO_PASSWORD)
    return True


def main() -> None:
    """Affiche l'écran courant."""
    st.set_page_config(page_title="Boss Fight", page_icon="⚔️")
    prepare_database()

    user = state.current_user()
    if user is not None:
        sidebar.render(user)

    with closing(repository.connect()) as conn:
        PAGES[state.current_page()](conn)


main()
