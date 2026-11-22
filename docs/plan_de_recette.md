# Plan de recette : vérifications manuelles

Les exigences vérifiées automatiquement sont dans la matrice de traçabilité (`docs/matrice_tracabilite.md`).
Ce plan couvre ce qu'un test automatique ne peut pas prouver. **Les colonnes « Résultat obtenu » et
« Preuve » sont à remplir pendant les essais** : n'y écris que ce que tu as réellement observé.

Version testée : ______ (URL en ligne ou « local »)   Date : ______   Testeur : ______

## TM-01 : Usabilité (BNF-03)

Critère : un nouvel utilisateur termine son premier combat en moins de 5 minutes, sans guide, et l'interface est en français.

Protocole : donner l'adresse de l'application à un camarade qui ne l'a jamais vue, ne rien expliquer, chronométrer
de l'ouverture de la page jusqu'à l'écran de résultat, noter les hésitations.

| Testeur | Temps (min:s) | Combat terminé ? | Où a-t-il hésité ? | Remarques |
|---|---|---|---|---|
| Camarade 1 | | | | |
| Camarade 2 | | | | |
| Camarade 3 | | | | |

Résultat : ___ / 3 testeurs sous 5 minutes. Interface entièrement en français : oui / non (écarts : ______)
Note : le bouton de téléversement de l'écran d'import (administrateur) affiche les textes par défaut de Streamlit, dans la langue du navigateur.

## TM-02 : Portabilité (BNF-06)

Scénario à rejouer dans chaque navigateur : se connecter avec le compte de démonstration, lancer un combat,
répondre à 3 questions (une erreur comprise), terminer le combat (ou en abandonner la lecture jusqu'au résultat),
ouvrir le tableau de bord, se déconnecter.

| Navigateur (version) | Accessible par l'URL sans installation | Scénario complet réussi | Problème rencontré | Capture n° |
|---|---|---|---|---|
| Chrome ______ | | | | |
| Firefox ______ | | | | |

## TM-03 : Disponibilité (BNF-07)

| Date et heure | URL répond | Temps de réveil de l'application (s) | Remarque |
|---|---|---|---|
| (la veille de la présentation) | | | |
| (le jour de la présentation) | | | |

Rappel : l'hébergement gratuit met l'application en veille après une période d'inactivité ; la première visite la réveille.

## TM-04 : Maintenabilité (BNF-05)

Commande : `pytest --cov=src --cov-report=term-missing`

| Couverture de la couche logique (%) | Objectif | Capture n° |
|---|---|---|
| | ≥ 70 | |

Les tests d'architecture (`tests/test_architecture.py`) vérifient en plus la séparation des 3 couches et les docstrings.

## TM-05 : Scénario de bout en bout sur la version en ligne

| N° | Action | Résultat attendu | Résultat obtenu | Capture n° |
|---|---|---|---|---|
| 1 | Ouvrir l'URL | Écran de connexion | | |
| 2 | Se connecter avec `demo` | Tableau de bord, chapitre listé avec son nombre de questions | | |
| 3 | Lancer un combat, répondre faux | Correction et explication, une vie en moins | | |
| 4 | Répondre juste | Le boss perd des PV | | |
| 5 | Aller jusqu'à la fin du combat | Écran de résultat (score, concepts à revoir) | | |
| 6 | Revenir au tableau de bord | Niveaux par concept et dates de révision | | |
| 7 | Ouvrir « Ma progression » | Courbe de maîtrise moyenne | | |
| 8 | Se déconnecter | Retour à l'écran de connexion | | |
| 9 | Se connecter en administrateur, importer un petit CSV valide | Questions importées affichées, chapitre visible | | |
| 10 | Importer un fichier mal formé | Message d'erreur, aucune donnée ajoutée | | |

## TM-06 : Modèle d'adaptation (BNF-08)

Les tests unitaires vérifient les formules. La comparaison avec un ordre aléatoire se fait par simulation
(livrable à part) : résultat à reporter ici une fois le script exécuté.

| Stratégie | Rétention moyenne estimée | Écart | Nombre d'élèves simulés |
|---|---|---|---|
| Ordre aléatoire | | | |
| Ordre adaptatif | | | |
