# Boss Fight

Application web qui transforme un cours en combat contre un boss : chaque bonne réponse lui retire des points de vie,
chaque erreur coûte une vie au joueur. Un **ordonnanceur adaptatif** (courbe d'oubli + niveau estimé par concept)
choisit les questions pour faire revoir ce qui est faible ou en train d'être oublié.

Projet individuel du module « Outils de travail collaboratif (Génie logiciel) », L2 CS, année 2026/2027.

- Application en ligne :[ _à compléter après le déploiement (voir `docs/deploiement.md`)_](https://boss-fightgit-zzakfjj2mlx5hfw7iouckn.streamlit.app/)
- Comptes de démonstration : `demo` / `demo-2026` (étudiant) ; le compte `admin` est protégé par un secret en ligne.

## Fonctionnalités

| Écran | Ce que fait l'application | Exigences |
|---|---|---|
| Connexion / inscription | Comptes avec mot de passe haché (PBKDF2), rôles étudiant et administrateur | BF-01, BF-02, BNF-02 |
| Tableau de bord | Chapitres disponibles, maîtrise par concept, dates de révision, « à revoir » | BF-03, BF-08 |
| Combat | Boss à 100 PV, 5 vies, dégâts selon la difficulté, correction et explication après chaque réponse | BF-04, BF-05, BF-06 |
| Résultat | Victoire ou défaite, score, concepts à revoir | BF-07 |
| Ma progression | Courbe de maîtrise moyenne combat après combat | BF-09 |
| Import (administrateur) | Ajout de questions par fichier CSV ou JSON, erreurs ligne par ligne | BF-10 |

Les numéros renvoient au cahier des charges. L'état de chaque exigence (testée automatiquement, manuellement ou non réalisée)
est dans `docs/matrice_tracabilite.md`.

## Installation et lancement

Prérequis : Python 3.10 ou plus récent.

```
python -m venv .venv
.venv\Scripts\activate          (Windows)      source .venv/bin/activate   (macOS / Linux)
pip install -r requirements.txt
streamlit run app.py
```

La base `boss_fight.db` est créée au premier lancement, avec les comptes de démonstration et 35 questions du chapitre 3.
On peut aussi la préparer à l'avance : `python init_db.py` (relançable sans danger).

Variables d'environnement facultatives :

| Variable | Rôle |
|---|---|
| `BOSS_FIGHT_ADMIN_PASSWORD` | Mot de passe du compte `admin` à sa création (par défaut : mot de passe de démonstration, à changer en ligne) |
| `BOSS_FIGHT_DB` | Chemin du fichier de base de données (par défaut `boss_fight.db` à la racine) |

## Tests

```
pytest                                          tous les tests
pytest --cov=src --cov-report=term-missing      avec la couverture du code
python -m tools.rtm                             régénère la matrice de traçabilité
```

- Tests unitaires de la logique (modèle de mémoire, règles du combat, choix des questions, authentification, import).
- Tests d'intégration sur une vraie base SQLite temporaire (combat complet, écriture atomique, performance avec 1000 questions).
- Tests d'architecture : l'interface n'accède jamais à la base, la logique n'importe jamais Streamlit, chaque fonction publique a une docstring.
- Tests d'acceptation de l'interface (`tests/test_ui_acceptance.py`) avec `streamlit.testing.v1.AppTest` : connexion, combat, victoire, défaite, import.
- Test de traçabilité : chaque exigence automatisable est couverte et la matrice publiée est à jour.
- Vérifications manuelles (usabilité, navigateurs, disponibilité) : `docs/plan_de_recette.md`.

## Architecture

Trois couches, avec des dépendances dans un seul sens (interface → logique → données) :

```
app.py                  point d'entrée Streamlit (aiguillage entre écrans)
src/
  config.py             constantes du jeu et du modèle
  ui/                   affichage uniquement (Streamlit)
  logic/                règles du jeu, modèle de mémoire, choix des questions, authentification, import
  data/                 accès SQLite : requêtes paramétrées uniquement, schema.sql
data/                   banque de questions du chapitre 3 (CSV et JSON)
tests/                  tests automatisés
tools/rtm.py            génère la matrice de traçabilité à partir des tests
docs/                   matrice de traçabilité, plan de recette, guide de déploiement
init_db.py              prépare la base de données
demo_console.py         démonstration du moteur en console
```

## Modèle d'adaptation

- Oubli : chance de se souvenir d'un concept `R = exp(-t / S)` (t en jours depuis la dernière révision, S = stabilité).
- Niveau : `P = 1 / (1 + exp(-(θ - b)))`, où b vaut −1, 0 ou +1 selon la difficulté de la question.
- Mise à jour après chaque réponse : `θ ← θ + 0,4 · (y − P)` ; `S` est multipliée par 1,8 si la réponse est juste, par 0,5 sinon (minimum 0,5).
- Choix : un concept est tiré avec une probabilité proportionnelle à `1 − R`, puis on prend la question dont la difficulté est la plus proche de `θ − 0,85`.
- Maîtrise affichée : `P` pour une question de difficulté moyenne, « à revoir » en dessous de 60 %.

## Format d'import des questions

CSV (virgule ou point-virgule) avec cette ligne d'en-tête :

```
concept,difficulte,enonce,option_a,option_b,option_c,option_d,bonne_reponse,explication
```

`difficulte` : facile, moyen ou difficile ; `bonne_reponse` : A, B, C ou D. Le fichier `data/banque_chapitre3.csv` sert d'exemple.
Le JSON est une liste d'objets avec les clés `concept`, `difficulte`, `enonce`, `options` (4 textes), `bonne_reponse`, `explication`.

## Méthode de travail

Scrum adapté à un projet individuel : 4 sprints de deux semaines, backlog priorisé par la méthode MoSCoW (Must / Should / Could),
un jalon livrable par sprint, tests écrits avec le code, historique Git lisible. Détails dans le rapport et le cahier des charges.

## Limites connues

- Sur l'hébergement gratuit, la base est recréée à chaque redémarrage : les comptes et progressions créés en ligne ne sont pas conservés (voir `docs/deploiement.md`).
- Non réalisée : BF-11, modifier ou supprimer des questions (priorité Could). Le retrait d'une question passe pour l'instant par la base de données.
- BF-09 (Should) prend la forme d'une courbe de maîtrise moyenne par combat terminé.
