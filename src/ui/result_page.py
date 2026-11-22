"""Écran de résultat d'un combat : victoire ou défaite, score, concepts à revoir (BF-07)."""

import streamlit as st

from src.config import BOSS_HP, WEAK_THRESHOLD
from src.logic import game_service
from src.logic.game_service import GameError
from src.ui import state


def render(conn) -> None:
    """Affiche le résultat du combat qui vient de se terminer."""
    session = st.session_state.get(state.BATTLE)
    if session is None:
        st.warning("Aucun combat à afficher.")
        if st.button("Retour au tableau de bord", key="result_back_empty"):
            state.go(state.DASHBOARD)
        return

    try:
        summary = game_service.finish_battle(conn, session)
    except GameError:
        st.warning("Ce combat n'est pas encore terminé.")
        if st.button("Reprendre le combat", key="result_resume"):
            state.go(state.BATTLE_PAGE)
        return

    if summary.victory:
        st.success("🏆 VICTOIRE ! Le boss est vaincu.")
        balloons_key = f"balloons_{session.battle_id}"
        if not st.session_state.get(balloons_key):
            st.session_state[balloons_key] = True  # les ballons ne partent qu'une fois, pas à chaque clic
            st.balloons()
    else:
        st.error("💀 DÉFAITE. Le boss a résisté, mais tu progresses à chaque combat.")
    st.caption(session.chapter.title)

    score_col, boss_col, lives_col = st.columns(3)
    score_col.metric("Score", f"{summary.correct_count} / {summary.answered_count}")
    boss_col.metric("PV du boss", f"{summary.boss_hp} / {BOSS_HP}")
    lives_col.metric("Vies restantes", summary.lives)

    with st.container(border=True):
        st.markdown(f"**Concepts à revoir** (réussite estimée inférieure à {WEAK_THRESHOLD:.0f} %)")
        if summary.weak_concepts:
            for concept, percent in summary.weak_concepts:
                st.markdown(f"- {concept} : {percent:.0f} %")
        else:
            st.markdown("Aucun : bravo, tous les concepts travaillés dépassent ce seuil. 🎉")

    replay_col, home_col = st.columns(2)
    if replay_col.button("Rejouer ce chapitre", key="result_replay"):
        try:
            st.session_state[state.BATTLE] = game_service.start_battle(conn, session.user, session.chapter.id)
        except GameError as error:
            st.error(str(error))
        else:
            state.go(state.BATTLE_PAGE)
    if home_col.button("Tableau de bord", key="result_home"):
        state.go(state.DASHBOARD)
