"""État de la session Streamlit : qui est connecté, quel écran est affiché, quel combat est en cours.

`st.session_state` est la mémoire d'un visiteur : elle survit entre deux clics, contrairement
aux variables Python ordinaires, qui sont recréées à chaque rerun du script.
"""

import streamlit as st

USER = "user"            # utilisateur connecté (objet User) ou absent
PAGE = "page"            # écran affiché : auth, dashboard, battle, result, progress, import
BATTLE = "battle_session"  # combat en cours (objet BattleSession)

AUTH, DASHBOARD, BATTLE_PAGE, RESULT, PROGRESS, IMPORT = (
    "auth", "dashboard", "battle", "result", "progress", "import",
)


def current_user():
    """Utilisateur connecté, ou None."""
    return st.session_state.get(USER)


def current_page() -> str:
    """Écran à afficher (l'écran de connexion tant que personne n'est connecté)."""
    if current_user() is None:
        return AUTH
    return st.session_state.get(PAGE, DASHBOARD)


def go(page: str) -> None:
    """Change d'écran et relance le script pour l'afficher."""
    st.session_state[PAGE] = page
    st.rerun()


def log_in(user) -> None:
    """Enregistre l'utilisateur connecté puis ouvre le tableau de bord."""
    st.session_state[USER] = user
    go(DASHBOARD)


def log_out() -> None:
    """Efface toute la session (utilisateur, combat en cours) et revient à l'écran de connexion."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
