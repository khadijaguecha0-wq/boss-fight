"""Petits éléments d'affichage réutilisables (barres colorées, cœurs). Aucune règle de jeu ici."""

import streamlit as st

from src.config import PLAYER_LIVES

LETTERS = "ABCD"
GREEN, ORANGE, RED, GREY = "#2e8b57", "#e0932b", "#c0392b", "#8a8f98"


def hearts(lives: int) -> str:
    """Les vies sous forme de cœurs : 3 vies sur 5 donnent ❤️❤️❤️🖤🖤."""
    lives = max(0, min(lives, PLAYER_LIVES))
    return "❤️" * lives + "🖤" * (PLAYER_LIVES - lives)


def level_color(percent: float | None) -> str:
    """Vert au-dessus de 60 %, orange entre 40 et 60 %, rouge en dessous, gris si non évalué."""
    if percent is None:
        return GREY
    if percent >= 60:
        return GREEN
    if percent >= 40:
        return ORANGE
    return RED


def bar(percent: float | None, color: str | None = None) -> None:
    """Barre de progression colorée (le texte du fond est neutre, donc lisible en thème clair et sombre)."""
    value = 0.0 if percent is None else max(0.0, min(percent, 100.0))
    color = color or level_color(percent)
    st.markdown(
        f'<div style="background:rgba(128,128,128,0.25);border-radius:6px;height:14px;width:100%;">'
        f'<div style="background:{color};width:{value:.0f}%;height:14px;border-radius:6px;"></div></div>',
        unsafe_allow_html=True,
    )
