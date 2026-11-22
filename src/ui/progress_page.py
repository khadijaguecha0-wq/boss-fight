"""Évolution de la maîtrise moyenne dans le temps (BF-09)."""

import pandas as pd
import streamlit as st

from src.logic import game_service
from src.ui import state


def render(conn) -> None:
    """Affiche la courbe de maîtrise moyenne, un point par combat terminé."""
    user = state.current_user()
    st.title("📈 Ma progression")
    points = game_service.progress_points(conn, user)
    if not points:
        st.info("Termine un combat pour voir ta courbe de progression.")
    else:
        table = pd.DataFrame(
            {
                "Combat": [f"n°{i} ({moment:%d/%m %H:%M})" for i, (moment, _) in enumerate(points, start=1)],
                "Maîtrise moyenne (%)": [round(value, 1) for _, value in points],
            }
        ).set_index("Combat")
        st.line_chart(table)
        st.caption("Maîtrise moyenne estimée sur les concepts du chapitre, à la fin de chaque combat.")
    if st.button("Retour au tableau de bord", key="progress_back"):
        state.go(state.DASHBOARD)
