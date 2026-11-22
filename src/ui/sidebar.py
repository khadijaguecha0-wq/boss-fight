"""Menu latéral : navigation entre les écrans et déconnexion (BF-02)."""

import streamlit as st

from src.ui import state


def render(user) -> None:
    """Affiche le menu pour l'utilisateur connecté."""
    with st.sidebar:
        st.markdown("### ⚔️ Boss Fight")
        role = " · administrateur" if user.is_admin else ""
        st.caption(f"Connecté : {user.username}{role}")
        if st.button("🏠 Tableau de bord", key="nav_dashboard"):
            state.go(state.DASHBOARD)
        if st.button("📈 Ma progression", key="nav_progress"):
            state.go(state.PROGRESS)
        if user.is_admin and st.button("📥 Importer des questions", key="nav_import"):
            state.go(state.IMPORT)
        st.divider()
        if st.button("Se déconnecter", key="nav_logout"):
            state.log_out()
