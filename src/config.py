"""Paramètres du jeu et du modèle d'adaptation.

Toutes les valeurs numériques du projet sont regroupées ici : pour ajuster le
jeu (plus de vies, dégâts différents...), on ne modifie que ce fichier.
"""

import os
from pathlib import Path

# --- Règles du combat (BF-04) ---
BOSS_HP = 100          # points de vie du boss au début d'un combat
PLAYER_LIVES = 5       # vies du joueur au début d'un combat

# Dégâts infligés au boss par une bonne réponse, selon la difficulté.
DAMAGE_BY_DIFFICULTY = {"facile": 10, "moyen": 15, "difficile": 20}

# --- Difficulté b d'une question dans le modèle logistique ---
DIFFICULTY_VALUE = {"facile": -1.0, "moyen": 0.0, "difficile": 1.0}

# --- Modèle de mémoire (section « Module d'adaptation » du cahier des charges) ---
INITIAL_THETA = 0.0        # niveau initial θ d'un étudiant sur un concept
INITIAL_STABILITY = 1.0    # stabilité initiale S, en jours
THETA_LEARNING_RATE = 0.4  # vitesse d'apprentissage du niveau θ
STABILITY_GAIN = 1.8       # S est multipliée par cette valeur après une bonne réponse
STABILITY_LOSS = 0.5       # S est multipliée par cette valeur après une erreur
MIN_STABILITY = 0.5        # S ne descend jamais sous ce minimum (en jours)

# --- Choix de la prochaine question (BF-06) ---
TARGET_OFFSET = 0.85   # difficulté visée : b = θ - 0,85, soit environ 70 % de réussite
MIN_WEIGHT = 0.05      # poids minimal d'un concept, pour qu'aucun ne soit jamais exclu

# --- Écran de résultat (BF-07) ---
WEAK_THRESHOLD = 60.0  # un concept est « à revoir » sous ce pourcentage de maîtrise

# --- Comptes et sécurité (BF-01, BF-02, BNF-02) ---
ROLE_STUDENT = "etudiant"
ROLE_ADMIN = "admin"
MIN_PASSWORD_LENGTH = 8        # longueur minimale d'un mot de passe
PBKDF2_ITERATIONS = 200_000    # nombre de tours du hachage PBKDF2 (plus c'est grand, plus c'est lent à casser)

# --- Fichiers du projet ---
BASE_DIR = Path(__file__).resolve().parent.parent
# La base peut être déplacée avec la variable d'environnement BOSS_FIGHT_DB.
DB_PATH = Path(os.environ.get("BOSS_FIGHT_DB", BASE_DIR / "boss_fight.db"))
DEFAULT_BANK_PATH = BASE_DIR / "data" / "banque_chapitre3.csv"
DEFAULT_CHAPTER_TITLE = "Chapitre 3 : Analyse et gestion des besoins"

# --- Comptes créés par le script d'initialisation (démonstration uniquement) ---
ADMIN_USERNAME = "admin"
DEMO_USERNAME = "demo"
DEFAULT_ADMIN_PASSWORD = "admin-demo-2026"   # à remplacer via BOSS_FIGHT_ADMIN_PASSWORD
DEFAULT_DEMO_PASSWORD = "demo-2026"
