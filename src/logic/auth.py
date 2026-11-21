"""Comptes utilisateurs : inscription, connexion, rôles (BF-01, BF-02, BNF-02).

Les mots de passe ne sont jamais stockés en clair : on enregistre un hachage PBKDF2
avec un sel aléatoire, sous la forme  pbkdf2_sha256$<tours>$<sel>$<hachage>.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime

from src.config import MIN_PASSWORD_LENGTH, PBKDF2_ITERATIONS, ROLE_STUDENT
from src.data import repository
from src.logic.models import User

ALGORITHM = "pbkdf2_sha256"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")
MAX_PASSWORD_LENGTH = 128
GENERIC_LOGIN_ERROR = "Pseudo ou mot de passe incorrect."


class AuthError(Exception):
    """Erreur d'inscription ou de connexion ; le message est affichable tel quel à l'étudiant."""


class PermissionDeniedError(Exception):
    """L'utilisateur n'a pas le droit d'effectuer cette action (ex. importer des questions)."""


def hash_password(password: str, salt: bytes | None = None, iterations: int | None = None) -> str:
    """Calcule le hachage salé d'un mot de passe, prêt à être enregistré en base."""
    salt = salt if salt is not None else secrets.token_bytes(16)
    iterations = iterations if iterations is not None else PBKDF2_ITERATIONS
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Vérifie un mot de passe par rapport au hachage enregistré (faux si le format est invalide)."""
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def register(
    conn: sqlite3.Connection,
    username: str,
    password: str,
    role: str = ROLE_STUDENT,
    now: datetime | None = None,
) -> User:
    """Crée un compte (BF-01). Lève `AuthError` avec un message clair si les données sont invalides.

    Le rôle est « etudiant » par défaut : seul le script d'initialisation crée un administrateur.
    """
    username = username.strip()
    if not USERNAME_PATTERN.match(username):
        raise AuthError(
            "Le pseudo doit contenir de 3 à 30 caractères : lettres, chiffres, point, tiret ou souligné."
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise AuthError(f"Le mot de passe ne doit pas dépasser {MAX_PASSWORD_LENGTH} caractères.")
    try:
        return repository.create_user(
            conn, username, hash_password(password), role, now or datetime.now()
        )
    except repository.UsernameTakenError:
        raise AuthError("Ce pseudo est déjà utilisé, choisis-en un autre.") from None


def login(conn: sqlite3.Connection, username: str, password: str) -> User:
    """Vérifie les identifiants (BF-02). Le message d'erreur est le même quel que soit le problème,
    pour ne pas révéler si un pseudo existe."""
    found = repository.get_user_with_hash(conn, username.strip())
    if found is None:
        hash_password(password)  # même temps de calcul que pour un vrai compte
        raise AuthError(GENERIC_LOGIN_ERROR)
    user, stored_hash = found
    if not verify_password(password, stored_hash):
        raise AuthError(GENERIC_LOGIN_ERROR)
    return user


def require_admin(user: User | None) -> None:
    """Lève `PermissionDeniedError` si l'utilisateur n'est pas administrateur (BNF-02)."""
    if user is None or not user.is_admin:
        raise PermissionDeniedError("Cette action est réservée à l'administrateur.")
