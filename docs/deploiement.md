# Déploiement sur Streamlit Community Cloud

L'application se déploie depuis le dépôt GitHub, sans serveur à gérer. (Les textes exacts de l'interface de
Streamlit peuvent légèrement changer ; la démarche reste la même.)

## Avant de commencer

1. Le dépôt GitHub `boss-fight` contient à sa racine `app.py` et `requirements.txt`.
2. `requirements.txt` contient au moins la ligne `streamlit` (les lignes `pytest` et `pytest-cov` sont inoffensives).
3. Tout est poussé : `git status` affiche « working tree clean » et `git push` ne signale rien à envoyer.
4. Le fichier `boss_fight.db` n'est pas dans le dépôt (il est ignoré par `.gitignore`).

## Étapes

1. Va sur https://share.streamlit.io et connecte-toi avec ton compte GitHub (autorise l'accès au dépôt si demandé).
2. Clique sur **Create app** (ou **New app**), puis **Deploy a public app from GitHub**.
3. Choisis le dépôt `boss-fight`, la branche `main`, et le fichier principal `app.py`.
4. Ouvre **Advanced settings** :
   - choisis Python 3.12 (ou 3.11) ;
   - dans **Secrets**, colle la ligne suivante en remplaçant la valeur par un vrai mot de passe que tu es seul à connaître :
     ```
     BOSS_FIGHT_ADMIN_PASSWORD = "remplace-moi-par-un-mot-de-passe-solide"
     ```
5. Clique sur **Deploy** et attends la fin de l'installation (1 à 3 minutes).
6. Note l'URL obtenue (de la forme `https://xxxx.streamlit.app`) : c'est l'adresse à donner au professeur.

## Pourquoi ce secret est indispensable

Le mot de passe administrateur par défaut est écrit dans `src/config.py`, donc visible par tous sur GitHub.
Sans le secret ci-dessus, n'importe qui pourrait se connecter en administrateur sur la version en ligne.
Le secret est lu par l'application sous forme de variable d'environnement (`BOSS_FIGHT_ADMIN_PASSWORD`).
Il ne s'applique qu'à la première création du compte : si l'application a déjà créé la base avec l'ancien mot de passe,
redémarre-la (menu de l'application, **Reboot**) pour recréer une base neuve.

## Limites de l'hébergement gratuit (à écrire dans le rapport)

- **Mise en veille** : après quelques jours sans visite, l'application s'endort ; la première visite la réveille (quelques secondes).
- **Disque non permanent** : à chaque redémarrage ou nouveau déploiement, la base SQLite est recréée par le script
  d'initialisation. Les comptes `admin` et `demo` et la banque de questions réapparaissent automatiquement ;
  **les comptes et progressions créés en ligne sont perdus**. Pour un usage durable, il faudrait une base hébergée
  (par exemple PostgreSQL) : c'est une perspective d'évolution.
- **Aucune garantie de service** : c'est pourquoi la disponibilité (BNF-07) est vérifiée la veille de la présentation.

## Après le déploiement

1. Rejoue le scénario `TM-05` de `docs/plan_de_recette.md` sur l'URL en ligne, avec captures d'écran.
2. Ajoute l'URL en haut du `README.md`.
3. Marque la version :
   ```
   git tag -a v1.0.0 -m "Version 1.0.0 de Boss Fight"
   git push origin v1.0.0
   ```
   Sur GitHub, onglet **Releases**, tu peux créer une « release » à partir de ce tag.
