"""Tableau de bord : choix du boss (BF-03) et maîtrise par concept (BF-08)."""

import streamlit as st

from src.logic import game_service
from src.logic.game_service import GameError
from src.ui import state
from src.ui.widgets import bar


def render(conn) -> None:
    """Affiche la liste des chapitres, puis la maîtrise de l'étudiant pour chaque concept."""
    user = state.current_user()
    st.title(f"Bonjour {user.username} 👋")

    st.subheader("Choisis ton boss")
    chapters = game_service.list_chapters(conn)
    if not chapters:
        st.info("Aucun chapitre pour l'instant. L'administrateur doit importer une banque de questions.")
    for chapter in chapters:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.markdown(f"**{chapter.title}**")
            left.caption(f"{chapter.question_count} questions")
            if chapter.question_count == 0:
                right.button("Indisponible", disabled=True, key=f"start_{chapter.id}")
            elif right.button("Combattre ⚔️", key=f"start_{chapter.id}"):
                try:
                    st.session_state[state.BATTLE] = game_service.start_battle(conn, user, chapter.id)
                except GameError as error:
                    st.error(str(error))
                else:
                    state.go(state.BATTLE_PAGE)

    st.subheader("Ma maîtrise par concept")
    lines = game_service.concept_lines(conn, user)
    if not lines:
        st.caption("Aucun concept pour l'instant.")
    current_chapter = None
    for line in lines:
        if line.chapter_title != current_chapter:
            current_chapter = line.chapter_title
            st.markdown(f"**{current_chapter}**")
        if line.percent is None:
            st.markdown(f"{line.concept} : *non évalué*")
        else:
            st.markdown(
                f"{line.concept} : **{line.percent:.0f} %** · {line.status} · "
                f"rétention estimée {line.retention:.0f} % · révisé le {line.last_review:%d/%m/%Y}"
            )
        bar(line.percent)

    if st.button("Voir ma progression dans le temps 📈", key="dashboard_to_progress"):
        state.go(state.PROGRESS)
