Fiches textuelles de cas d'utilisation - Boss Fight

Structure canonique vue en cours : acteur principal, pré-conditions, scénario nominal, scénarios alternatifs / exceptions, post-conditions.

UC-04 : Combattre un boss (BF-04 à BF-07)

Acteur principal : Étudiant.

Pré-conditions : l'étudiant est authentifié (UC-02) et a choisi un chapitre contenant au moins une question (UC-03).

Scénario nominal

Le système crée un combat : le boss a 100 PV, le joueur a 5 vies.
Le système sélectionne une question adaptée (concept à fort risque d'oubli, difficulté visant environ 70 % de réussite) et l'affiche avec ses 4 options.
L'étudiant choisit une option.
Le système vérifie la réponse et retire des PV au boss (10, 15 ou 20 selon la difficulté).
Le système met à jour le niveau et la stabilité du concept et enregistre la réponse.
Le système affiche la correction et l'explication.
Les étapes 2 à 6 se répètent jusqu'à ce que le boss atteigne 0 PV.
Le système affiche l'écran de résultat : victoire, score, concepts à revoir.

Scénarios alternatifs / exceptions

4a. La réponse est mauvaise : le système retire 1 vie au joueur (le boss ne perd pas de PV).
7a. Le joueur n'a plus de vie : le combat s'arrête sur une défaite, puis étape 8.
7b. Il n'y a plus de question disponible : le combat s'arrête, et le résultat est une défaite si le boss a encore des PV, puis étape 8. (Choix de conception, à confirmer dans le rapport.)
5a. L'enregistrement en base échoue : le système affiche un message d'erreur, ignore cette réponse et poursuit le combat.

Post-conditions : le combat est enregistré avec son statut final (victoire ou défaite) ; chaque réponse est stockée ; le niveau et la stabilité des concepts travaillés sont à jour.

UC-07 : Importer une banque de questions (BF-10)

Acteur principal : Administrateur.

Pré-conditions : l'administrateur est authentifié (UC-02) avec le rôle administrateur ; il dispose d'un fichier CSV ou JSON de questions.

Scénario nominal

L'administrateur ouvre la page d'import.
Il choisit le fichier et indique le nom du chapitre.
Le système lit le fichier et valide chaque question (énoncé, 4 options, une seule bonne réponse, concept, difficulté, explication).
Le système enregistre les questions valides, en créant le chapitre et les concepts si nécessaire.
Le système affiche le nombre de questions importées et rejetées.

Scénarios alternatifs / exceptions

1a. L'utilisateur n'est pas administrateur : l'accès est refusé.
3a. Le fichier est illisible ou son format n'est pas pris en charge : le système affiche un message d'erreur et n'importe rien.
3b. Une ligne est invalide : elle est rejetée avec son numéro ; les autres lignes sont importées.

Post-conditions : les questions valides sont disponibles pour le choix d'un boss (UC-03) ; aucune ligne invalide n'est stockée.

Début de la matrice de traçabilité (RTM)
Besoin	Cas d'utilisation	Priorité
BF-01 Créer un compte	UC-01	Must
BF-02 Se connecter / déconnecter	UC-02	Must
BF-03 Choisir un chapitre	UC-03	Must
BF-04 à BF-07 Combat, explication, questions adaptées, résultat	UC-04	Must
BF-08 Tableau de bord	UC-05	Must
BF-09 Progression dans le temps	UC-06	Should
BF-10 Importer des questions	UC-07	Must
BF-11 Modifier ou supprimer des questions	UC-08	Could

Les colonnes « Cas de test » et « Module du code » seront ajoutées aux étapes 4 à 7.