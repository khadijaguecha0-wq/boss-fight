"""Importation d'une banque de questions par l'administrateur (BF-10, BNF-02)."""

import streamlit as st

from src.logic import importer
from src.logic.auth import PermissionDeniedError
from src.ui import state


def render(conn) -> None:
    """Affiche le formulaire d'import, réservé à l'administrateur."""
    user = state.current_user()
    st.title("📥 Importer des questions")
    if not user.is_admin:  # contrôle d'accès : même si quelqu'un atteint cet écran, il est refusé
        st.error("Cet écran est réservé à l'administrateur.")
        return

    st.write(
        "Chaque question contient : concept, difficulté (facile, moyen, difficile), énoncé, "
        "4 options, bonne réponse (A, B, C ou D) et explication. Formats acceptés : CSV ou JSON."
    )
    st.download_button(
        "Télécharger un modèle CSV", data=importer.CSV_TEMPLATE.encode("utf-8"),
        file_name="modele_questions.csv", mime="text/csv", key="download_template",
    )

    with st.form("import_form"):
        title = st.text_input("Titre du chapitre", key="import_title")
        uploaded = st.file_uploader("Fichier de questions", type=["csv", "json"], key="import_file")
        submitted = st.form_submit_button("Importer")
    if not submitted:
        return
    if uploaded is None:
        st.warning("Choisis d'abord un fichier .csv ou .json.")
        return

    try:
        fmt = importer.detect_format(uploaded.name)
        content = importer.decode_upload(uploaded.getvalue())
        report = importer.import_questions(conn, user, title, content, fmt)
    except (ValueError, PermissionDeniedError) as error:
        st.error(str(error))
        return

    if report.file_error:
        st.error(f"Fichier refusé : {report.file_error}")
        return
    st.success(f"{report.imported} question(s) importée(s).")
    if report.rejected:
        st.warning(f"{len(report.rejected)} ligne(s) rejetée(s) :")
        for error in report.rejected:
            st.markdown(f"- {error}")
