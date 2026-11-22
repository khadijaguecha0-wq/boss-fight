"""Écran de combat : question, correction et explication (BF-04, BF-05)."""

import streamlit as st

from src.config import BOSS_HP
from src.logic import game_service
from src.logic.game_service import GameError
from src.logic.memory_model import mastery_percent
from src.ui import state
from src.ui.widgets import LETTERS, RED, bar, hearts


def render(conn) -> None:
    """Affiche l'état du combat, puis la question ou sa correction."""
    session = st.session_state.get(state.BATTLE)
    if session is None:
        st.warning("Aucun combat en cours. Choisis un boss depuis le tableau de bord.")
        if st.button("Retour au tableau de bord", key="battle_back"):
            state.go(state.DASHBOARD)
        return

    battle = session.battle
    st.title(f"⚔️ {session.chapter.title}")

    boss_col, lives_col = st.columns([3, 2])
    boss_col.markdown(f"**PV du boss** : {battle.boss_hp} / {BOSS_HP}")
    with boss_col:
        bar(100.0 * battle.boss_hp / BOSS_HP, color=RED)
    lives_col.markdown(f"**Vies** : {hearts(battle.lives)}")

    question = session.current
    if question is None:  # combat terminé et déjà corrigé : on ne peut aller que vers le résultat
        state.go(state.RESULT)
        return

    with st.container(border=True):
        st.caption(f"Concept : {question.concept} · difficulté : {question.difficulty}")
        st.subheader(question.text)
        if session.last_result is None:
            _render_question(conn, session)
        else:
            _render_correction(conn, session)


def _render_question(conn, session) -> None:
    question = session.current
    labels = [f"{LETTERS[i]}. {option}" for i, option in enumerate(question.options)]
    with st.form(key=f"answer_form_{question.id}"):
        picked = st.radio("Ta réponse", labels, index=None, key=f"choice_{question.id}")
        submitted = st.form_submit_button("Valider ⚔️")
    if submitted:
        if picked is None:
            st.warning("Choisis une réponse avant de valider.")
            return
        try:
            game_service.submit_answer(conn, session, labels.index(picked))
        except GameError as error:
            st.error(str(error))
            return
        st.rerun()


def _render_correction(conn, session) -> None:
    question, result = session.current, session.last_result
    if result.correct:
        st.success(f"✅ Bonne réponse ! Le boss perd {result.damage} PV.")
    else:
        st.error("❌ Mauvaise réponse : tu perds 1 vie.")
    st.markdown(f"**Bonne réponse** : {LETTERS[result.correct_index]}. {question.options[result.correct_index]}")
    if result.explanation:
        st.info(result.explanation)
    st.caption(f"Maîtrise de « {result.concept} » : {mastery_percent(result.new_mastery):.0f} %")

    if session.battle.is_over():
        if st.button("Voir le résultat 🏁", key=f"to_result_{question.id}"):
            state.go(state.RESULT)
    elif st.button("Question suivante ➡️", key=f"next_{question.id}"):
        try:
            game_service.next_question(conn, session)
        except GameError as error:
            st.error(str(error))
            return
        st.rerun()
