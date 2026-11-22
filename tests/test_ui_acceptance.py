"""Tests d'acceptation de l'interface : on pilote l'application Streamlit comme le ferait un utilisateur.

Ils utilisent `streamlit.testing.v1.AppTest`, qui exécute `app.py` sans navigateur. L'application est
branchée sur une base temporaire : ta vraie base `boss_fight.db` n'est jamais touchée.
Le téléversement de fichier (écran d'import) n'est pas simulable par AppTest : l'import est couvert
par les tests de `test_importer.py`.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402  (après le contrôle de présence de Streamlit)

APP_FILE = str(Path(__file__).resolve().parent.parent / "app.py")
ADMIN_PASSWORD = "admin-test-123"


@pytest.fixture
def app(tmp_path, monkeypatch):
    """L'application complète démarrée sur une base temporaire (comptes demo et admin, 35 questions)."""
    import streamlit as st
    from src import config

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "ui_test.db")
    monkeypatch.setenv("BOSS_FIGHT_ADMIN_PASSWORD", ADMIN_PASSWORD)
    st.cache_resource.clear()  # la préparation de la base doit se refaire sur la base temporaire
    at = AppTest.from_file(APP_FILE, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    yield at
    st.cache_resource.clear()


# ---------- Gestes de l'utilisateur ----------

def press(at, label):
    """Clique sur le bouton qui porte ce texte."""
    next(button for button in at.button if button.label == label).click().run()
    assert not at.exception, at.exception


def log_in(at, username="demo", password="demo-2026"):
    at.text_input(key="login_username").input(username)
    at.text_input(key="login_password").input(password)
    press(at, "Se connecter")


def start_first_battle(at):
    at.button(key="start_1").click().run()
    assert not at.exception, at.exception


def answer(at, correct):
    """Choisit une option (juste ou fausse) pour la question affichée et valide. Renvoie la question."""
    question = at.session_state["battle_session"].current
    radio = at.radio(key=f"choice_{question.id}")
    index = question.correct_index if correct else (question.correct_index + 1) % 4
    radio.set_value(radio.options[index])
    press(at, "Valider ⚔️")
    return question


def texts(elements):
    return [element.value for element in elements]


# ---------- BF-01, BF-02 : comptes ----------

def test_the_login_screen_is_shown_first(app):
    """BF-02 : sans être connecté, on arrive sur l'écran de connexion."""
    assert "Boss Fight" in app.title[0].value
    assert "user" not in app.session_state


def test_wrong_password_is_refused_with_a_generic_message(app):
    """BF-02 : des identifiants invalides sont refusés avec un message qui ne dit pas lequel est faux."""
    log_in(app, "demo", "mauvais-mot-de-passe")
    assert any("incorrect" in message for message in texts(app.error))
    assert "user" not in app.session_state


def test_valid_login_opens_the_dashboard(app):
    """BF-02 : des identifiants valides ouvrent le tableau de bord."""
    log_in(app)
    assert "Bonjour demo" in app.title[0].value


def test_registration_is_validated_then_logs_the_new_student_in(app):
    """BF-01 : mots de passe différents, trop court et pseudo pris sont refusés ; un compte valide est créé."""
    def fill(username, password, confirmation):
        app.text_input(key="register_username").input(username)
        app.text_input(key="register_password").input(password)
        app.text_input(key="register_confirmation").input(confirmation)
        press(app, "Créer mon compte")

    fill("nouveau", "motdepasse1", "autre-chose")
    assert any("différents" in message for message in texts(app.error))
    fill("nouveau", "court", "court")
    assert any("au moins 8" in message for message in texts(app.error))
    fill("demo", "motdepasse1", "motdepasse1")
    assert any("déjà utilisé" in message for message in texts(app.error))
    fill("nouveau", "motdepasse1", "motdepasse1")
    assert "Bonjour nouveau" in app.title[0].value


def test_logout_returns_to_the_login_screen(app):
    """BF-02 : la déconnexion ramène à l'écran de connexion et efface la session."""
    log_in(app)
    app.sidebar.button(key="nav_logout").click().run()
    assert "user" not in app.session_state
    assert "Boss Fight" in app.title[0].value


# ---------- BF-03, BF-08 : tableau de bord ----------

def test_dashboard_lists_the_chapter_with_its_number_of_questions(app):
    """BF-03 : le chapitre est proposé avec son nombre de questions."""
    log_in(app)
    assert any("35 questions" in caption for caption in texts(app.caption))
    assert app.button(key="start_1") is not None


def test_new_student_sees_every_concept_as_not_evaluated(app):
    """BF-08 : un étudiant qui n'a rien révisé voit tous les concepts « non évalués »."""
    log_in(app)
    assert sum("non évalué" in line for line in texts(app.markdown)) == 8


# ---------- BF-04, BF-05, BF-07 : combat ----------

def test_battle_screen_shows_boss_hit_points_lives_and_a_question(app):
    """BF-04 : le combat affiche le boss à 100 PV, 5 vies et une question à 4 options."""
    log_in(app)
    start_first_battle(app)
    page = " ".join(texts(app.markdown))
    assert "100 / 100" in page and "❤️❤️❤️❤️❤️" in page
    question = app.session_state["battle_session"].current
    assert len(app.radio(key=f"choice_{question.id}").options) == 4


def test_wrong_answer_shows_the_correction_and_costs_a_life(app):
    """BF-04, BF-05 : une erreur coûte une vie, et la bonne réponse avec l'explication s'affiche."""
    log_in(app)
    start_first_battle(app)
    question = answer(app, correct=False)
    assert any("Mauvaise réponse" in message for message in texts(app.error))
    assert any(question.explanation in message for message in texts(app.info))
    assert "❤️❤️❤️❤️🖤" in " ".join(texts(app.markdown))


def test_correct_answer_hurts_the_boss(app):
    """BF-04 : une bonne réponse retire des PV au boss."""
    log_in(app)
    start_first_battle(app)
    answer(app, correct=True)
    assert any("Le boss perd" in message for message in texts(app.success))
    assert app.session_state["battle_session"].battle.boss_hp < 100


def test_five_mistakes_end_in_a_defeat_screen_with_concepts_to_review(app):
    """BF-04, BF-07 : cinq erreurs mènent à l'écran de défaite, qui liste les concepts à revoir."""
    log_in(app)
    start_first_battle(app)
    for mistake in range(5):
        question = answer(app, correct=False)
        target = f"to_result_{question.id}" if mistake == 4 else f"next_{question.id}"
        app.button(key=target).click().run()
    assert any("DÉFAITE" in message for message in texts(app.error))
    assert any("Concepts à revoir" in line for line in texts(app.markdown))


def test_answering_correctly_until_the_end_gives_a_victory(app):
    """BF-04, BF-07 : en répondant juste jusqu'au bout, le boss tombe et l'écran de victoire s'affiche."""
    log_in(app)
    start_first_battle(app)
    for _ in range(40):  # garde-fou : un combat gagné ne dépasse pas la quinzaine de questions
        question = answer(app, correct=True)
        if app.session_state["battle_session"].battle.is_over():
            app.button(key=f"to_result_{question.id}").click().run()
            break
        app.button(key=f"next_{question.id}").click().run()
    assert any("VICTOIRE" in message for message in texts(app.success))
    assert app.session_state["battle_session"].battle.boss_hp == 0


# ---------- BF-08, BF-09 : suivi après un combat ----------

def test_dashboard_and_progress_page_reflect_a_finished_battle(app):
    """BF-08, BF-09 : après un combat, le tableau de bord montre des niveaux et la progression a sa courbe."""
    log_in(app)
    start_first_battle(app)
    for mistake in range(5):
        question = answer(app, correct=False)
        target = f"to_result_{question.id}" if mistake == 4 else f"next_{question.id}"
        app.button(key=target).click().run()
    app.sidebar.button(key="nav_dashboard").click().run()
    assert any("%" in line and "À revoir" in line for line in texts(app.markdown))

    app.sidebar.button(key="nav_progress").click().run()
    assert not any("Termine un combat" in message for message in texts(app.info))
    assert any("Maîtrise moyenne estimée" in caption for caption in texts(app.caption))


def test_progress_page_is_empty_before_any_battle(app):
    """BF-09 : sans combat terminé, la page de progression invite à en terminer un."""
    log_in(app)
    app.sidebar.button(key="nav_progress").click().run()
    assert any("Termine un combat" in message for message in texts(app.info))


# ---------- BF-10, BNF-02 : droits d'administrateur ----------

def test_import_menu_is_only_visible_to_the_administrator(app):
    """BNF-02 : le menu d'import n'existe que pour l'administrateur."""
    log_in(app)
    assert [b for b in app.sidebar.button if b.key == "nav_import"] == []
    app.sidebar.button(key="nav_logout").click().run()
    log_in(app, "admin", ADMIN_PASSWORD)
    assert [b for b in app.sidebar.button if b.key == "nav_import"] != []


def test_a_student_who_reaches_the_import_screen_is_refused(app):
    """BNF-02 : même en atteignant l'écran d'import, un étudiant est refusé."""
    log_in(app)
    app.session_state["page"] = "import"
    app.run()
    assert any("réservé à l'administrateur" in message for message in texts(app.error))


def test_the_administrator_can_open_the_import_screen(app):
    """BF-10 : l'administrateur accède à l'écran d'import."""
    log_in(app, "admin", ADMIN_PASSWORD)
    app.sidebar.button(key="nav_import").click().run()
    assert "Importer des questions" in app.title[0].value
    assert not texts(app.error)
