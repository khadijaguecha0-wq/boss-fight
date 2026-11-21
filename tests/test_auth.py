"""Tests des comptes : hachage, inscription, connexion, rôles (BF-01, BF-02, BNF-02)."""

import pytest

from src.config import PBKDF2_ITERATIONS as PRODUCTION_ITERATIONS
from src.logic import auth
from src.logic.auth import AuthError, PermissionDeniedError


# ---------- Hachage des mots de passe ----------

def test_hash_has_expected_format_and_hides_the_password():
    """BNF-02 : le hachage a la forme algorithme$tours$sel$empreinte et ne contient pas le mot de passe."""
    stored = auth.hash_password("secret-long")
    algorithm, iterations, salt, digest = stored.split("$")
    assert algorithm == "pbkdf2_sha256"
    assert int(iterations) == 1000  # valeur réduite pendant les tests (voir conftest)
    assert len(salt) == 32 and len(digest) == 64
    assert "secret-long" not in stored


def test_same_password_gives_different_hashes_thanks_to_salt():
    """BNF-02 : le sel aléatoire fait que deux comptes avec le même mot de passe ont des hachages différents."""
    assert auth.hash_password("meme-mot-de-passe") != auth.hash_password("meme-mot-de-passe")


def test_verify_password_accepts_right_and_refuses_wrong():
    """BF-02 : le bon mot de passe est accepté, un autre est refusé."""
    stored = auth.hash_password("bon-mot-de-passe")
    assert auth.verify_password("bon-mot-de-passe", stored) is True
    assert auth.verify_password("mauvais-mot-de-passe", stored) is False


@pytest.mark.parametrize("broken", ["", "abc", "md5$1$00$00", "pbkdf2_sha256$x$zz$zz", "pbkdf2_sha256$1$00"])
def test_verify_password_refuses_malformed_hashes(broken):
    """Robustesse : un hachage mal formé ne fait jamais planter la vérification, il est refusé."""
    assert auth.verify_password("n-importe-quoi", broken) is False


def test_verification_uses_the_iteration_count_stored_in_the_hash():
    """Évolutivité : un ancien hachage reste valable même si le nombre de tours par défaut change."""
    stored = auth.hash_password("mot-de-passe-1", iterations=500)
    assert auth.verify_password("mot-de-passe-1", stored) is True


def test_production_iteration_count_is_strong():
    """BNF-02 : en production, le hachage fait au moins 100 000 tours."""
    assert PRODUCTION_ITERATIONS >= 100_000


# ---------- Inscription ----------

def test_register_creates_a_student_account(conn, now):
    """BF-01 : un compte étudiant est créé avec un pseudo et un mot de passe valides."""
    user = auth.register(conn, "alice", "motdepasse1", now=now)
    assert user.username == "alice"
    assert user.role == "etudiant"
    assert user.is_admin is False


def test_register_never_stores_the_password_in_clear(conn, now):
    """BNF-02 : en base, on ne trouve que le hachage salé."""
    auth.register(conn, "alice", "motdepasse1", now=now)
    stored = conn.execute("SELECT password_hash FROM users WHERE username = 'alice'").fetchone()[0]
    assert stored.startswith("pbkdf2_sha256$")
    assert "motdepasse1" not in stored


def test_register_refuses_an_existing_username_with_explicit_message(conn, now):
    """BF-01 : un pseudo déjà pris est refusé avec un message clair, même avec d'autres majuscules."""
    auth.register(conn, "alice", "motdepasse1", now=now)
    with pytest.raises(AuthError, match="déjà utilisé"):
        auth.register(conn, "ALICE", "autremotdepasse", now=now)


def test_register_refuses_a_short_password(conn, now):
    """BF-01 : un mot de passe de moins de 8 caractères est refusé."""
    with pytest.raises(AuthError, match="au moins 8"):
        auth.register(conn, "alice", "court", now=now)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_register_refuses_an_absurdly_long_password(conn, now):
    """BF-01 : un mot de passe démesuré (plus de 128 caractères) est refusé, pour éviter les abus."""
    with pytest.raises(AuthError, match="128"):
        auth.register(conn, "alice", "x" * 129, now=now)


@pytest.mark.parametrize("bad_username", ["", "ab", "a b c", "x" * 31, "é@!?"])
def test_register_refuses_invalid_usernames(conn, now, bad_username):
    """BF-01 : un pseudo vide, trop court, trop long ou avec des caractères interdits est refusé."""
    with pytest.raises(AuthError, match="pseudo"):
        auth.register(conn, bad_username, "motdepasse1", now=now)


def test_register_ignores_spaces_around_the_username(conn, now):
    """BF-01 : les espaces au début et à la fin du pseudo sont retirés."""
    user = auth.register(conn, "  alice  ", "motdepasse1", now=now)
    assert user.username == "alice"


# ---------- Connexion ----------

def test_login_with_valid_credentials(conn, student):
    """BF-02 : des identifiants valides donnent accès au compte."""
    user = auth.login(conn, "alice", "motdepasse1")
    assert user == student


def test_login_ignores_username_case(conn, student):
    """BF-02 : le pseudo n'est pas sensible aux majuscules."""
    assert auth.login(conn, "ALICE", "motdepasse1").id == student.id


def test_login_failures_all_give_the_same_generic_message(conn, student):
    """BF-02 : mauvais mot de passe ou pseudo inconnu donnent le même message, qui ne révèle rien."""
    with pytest.raises(AuthError) as wrong_password:
        auth.login(conn, "alice", "mauvais-mot-de-passe")
    with pytest.raises(AuthError) as unknown_user:
        auth.login(conn, "personne", "motdepasse1")
    assert str(wrong_password.value) == str(unknown_user.value) == auth.GENERIC_LOGIN_ERROR


# ---------- Rôles ----------

def test_student_is_refused_admin_actions(student):
    """BNF-02 : un étudiant n'a pas le droit d'accéder aux fonctions d'administration."""
    with pytest.raises(PermissionDeniedError):
        auth.require_admin(student)


def test_nobody_logged_in_is_refused_admin_actions():
    """BNF-02 : sans utilisateur connecté, l'accès administrateur est refusé."""
    with pytest.raises(PermissionDeniedError):
        auth.require_admin(None)


def test_admin_passes_the_admin_check(admin):
    """BNF-02 : l'administrateur est autorisé."""
    auth.require_admin(admin)  # ne lève aucune exception
    assert admin.is_admin is True
