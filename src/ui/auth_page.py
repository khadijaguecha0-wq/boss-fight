"""Écran de connexion et de création de compte (BF-01, BF-02)."""

import streamlit as st

from src.logic import auth
from src.logic.auth import AuthError
from src.ui import state


def render(conn) -> None:
    """Affiche les deux formulaires : se connecter, créer un compte."""
    st.title("⚔️ Boss Fight")
    st.write(
        "Révise tes cours en affrontant un boss : chaque bonne réponse lui fait des dégâts, "
        "chaque erreur te coûte une vie. L'application choisit les questions selon ton niveau "
        "et ce que tu risques d'oublier."
    )

    login_tab, register_tab = st.tabs(["Se connecter", "Créer un compte"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Pseudo", key="login_username")
            password = st.text_input("Mot de passe", type="password", key="login_password")
            submitted = st.form_submit_button("Se connecter")
        if submitted:
            try:
                user = auth.login(conn, username, password)
            except AuthError as error:
                st.error(str(error))
            else:
                state.log_in(user)

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Choisis un pseudo", key="register_username")
            new_password = st.text_input("Mot de passe (8 caractères minimum)", type="password", key="register_password")
            confirmation = st.text_input("Confirme le mot de passe", type="password", key="register_confirmation")
            created = st.form_submit_button("Créer mon compte")
        if created:
            if new_password != confirmation:
                st.error("Les deux mots de passe sont différents.")
            else:
                try:
                    user = auth.register(conn, new_username, new_password)
                except AuthError as error:
                    st.error(str(error))
                else:
                    state.log_in(user)
