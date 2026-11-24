# Simulation : ordre adaptatif contre ordre aléatoire (BNF-08)

Rapport généré par `python -m tools.simulation` (voir le haut du fichier `tools/simulation.py`).
Élèves simulés par scénario : 1000. Graine du hasard : 2026 (mêmes chiffres à chaque lancement).

## Question posée

Pour un même nombre de questions posées, choisir les questions avec le modèle de l'application (courbe d'oubli + niveau par concept) fait-il mieux retenir qu'un tirage au hasard ?

## Méthode

- Chaque élève simulé révise pendant 5 séances (jours 0, 1, 3, 6, 10), avec 12 questions par séance, dans les deux cas.
- Le cours a été suivi 5 jours avant la première séance. L'examen blanc a lieu le jour 14 et reprend toutes les questions de la banque (35 questions, 8 concepts, la vraie banque de l'application).
- Ordre aléatoire : les questions sont tirées au hasard, sans répétition dans une séance.
- Ordre adaptatif : le vrai code de l'application (`choose_question` et `update_mastery`).
- La mémoire de l'élève est cachée : l'application ne voit que ses réponses. La probabilité de répondre juste vaut 0.25 + 0.75 × souvenir × niveau (4 options : on peut deviner).
- Le score à l'examen est le score attendu calculé avec la mémoire cachée, jamais avec l'estimation de l'application.
- Comparaison appariée : le même élève, avec la même suite de nombres aléatoires pour ses réponses, révise une fois dans chaque ordre.
- « Sans révision » : le même élève passe l'examen sans avoir révisé (point de référence).

## Résultats

### Scénario A : Mémoire différente du modèle

Cas principal. La mémoire cachée n'obéit pas aux mêmes constantes que l'application : oubli plus lent ou plus rapide selon l'élève, et une erreur suivie de l'explication fait quand même progresser la mémoire (l'application, elle, la pénalise).

| Stratégie | Score attendu à l'examen (%) | Intervalle à 95 % | Concepts sous 60 % à l'examen |
|---|---|---|---|
| Sans révision | 25.0 | - | - |
| Ordre aléatoire | 72.4 | 71.8 à 72.9 | 1.92 sur 8 |
| Ordre adaptatif | 74.5 | 74.0 à 75.1 | 1.28 sur 8 |

Écart adaptatif moins aléatoire : +2.18 points (intervalle à 95 % : +2.05 à +2.31). L'ordre adaptatif est meilleur pour 86 % des élèves.

L'ordre adaptatif donne un meilleur score attendu : +2.2 points (intervalle à 95 % : de 2.0 à 2.3).

### Scénario B : Mémoire qui suit les règles de l'application

La mémoire cachée suit exactement les règles de mise à jour de l'application (stabilité ×1,8 après une réussite, ×0,5 après une erreur, niveau mis à jour par la même formule). Valeurs de départ identiques à celles du scénario A : A et B ne diffèrent que par les règles de mise à jour.

| Stratégie | Score attendu à l'examen (%) | Intervalle à 95 % | Concepts sous 60 % à l'examen |
|---|---|---|---|
| Sans révision | 25.0 | - | - |
| Ordre aléatoire | 35.2 | 34.8 à 35.6 | 7.00 sur 8 |
| Ordre adaptatif | 35.5 | 35.1 à 35.9 | 6.93 sur 8 |

Écart adaptatif moins aléatoire : +0.36 points (intervalle à 95 % : +0.02 à +0.70). L'ordre adaptatif est meilleur pour 52 % des élèves.

L'ordre adaptatif donne un meilleur score attendu, mais l'écart est très faible : +0.4 point (intervalle à 95 % : de 0.0 à 0.7).

### Scénario C : Règles de l'application, élèves forts

Comme B, mais les élèves connaissent déjà bien le cours au départ (niveau moyen +2 au lieu de -0,3). Sert à vérifier que l'absence d'écart en B ne vient pas seulement d'élèves trop faibles.

| Stratégie | Score attendu à l'examen (%) | Intervalle à 95 % | Concepts sous 60 % à l'examen |
|---|---|---|---|
| Sans révision | 25.1 | - | - |
| Ordre aléatoire | 53.7 | 53.0 à 54.3 | 4.63 sur 8 |
| Ordre adaptatif | 54.4 | 53.8 à 55.1 | 4.34 sur 8 |

Écart adaptatif moins aléatoire : +0.77 points (intervalle à 95 % : +0.25 à +1.29). L'ordre adaptatif est meilleur pour 54 % des élèves.

L'ordre adaptatif donne un meilleur score attendu, mais l'écart est très faible : +0.8 point (intervalle à 95 % : de 0.3 à 1.3).

### Remarque sur les constantes du modèle

Avec une stabilité multipliée par 1.8 après une réussite et par 0.5 après une erreur, la stabilité d'un concept n'augmente en moyenne que si le taux de réussite dépasse 54 %. Les scénarios B et C, où la mémoire cachée suit ces règles, sont cohérents avec cette propriété : les élèves y retiennent peu à 14 jours quel que soit l'ordre des questions. Ce lien n'est pas démontré ici.

## Sensibilité (scénario A)

Écart de score attendu (adaptatif moins aléatoire, en points) quand on change le protocole :

| Questions par séance | Examen au jour | Aléatoire (%) | Adaptatif (%) | Écart (points) | Intervalle à 95 % |
|---|---|---|---|---|---|
| 8 | 7 | 69.9 | 72.4 | +2.48 | +2.33 à +2.62 |
| 8 | 14 | 58.1 | 61.5 | +3.41 | +3.24 à +3.57 |
| 8 | 28 | 44.6 | 45.0 | +0.43 | +0.22 à +0.63 |
| 12 | 7 | 78.3 | 79.0 | +0.69 | +0.61 à +0.76 |
| 12 | 14 | 72.4 | 74.5 | +2.18 | +2.05 à +2.31 |
| 12 | 28 | 62.1 | 64.5 | +2.39 | +2.20 à +2.57 |
| 20 | 7 | 88.3 | 88.4 | +0.07 | +0.02 à +0.12 |
| 20 | 14 | 87.3 | 87.6 | +0.28 | +0.22 à +0.34 |
| 20 | 28 | 84.7 | 85.4 | +0.71 | +0.60 à +0.81 |

## Limites (à écrire dans le rapport)

- C'est une simulation : les élèves sont des modèles mathématiques. Elle montre que le choix des questions est cohérent avec une mémoire qui oublie, pas qu'il améliore les résultats de vrais étudiants. Seule une expérience avec de vrais étudiants pourrait le démontrer.
- Les résultats dépendent des hypothèses du simulateur (oubli exponentiel, valeurs des paramètres cachés). Le scénario A les écarte volontairement de celles de l'application ; les scénarios B et C les reprennent.
- La banque est petite (35 questions) : une même question revient d'une séance à l'autre.
- Le protocole (5 séances, 12 questions par séance, examen au jour 14) et le scénario A ont été fixés avant le premier lancement et n'ont jamais été modifiés pour améliorer leur résultat. Une première version du scénario B (stabilité de départ de 1 jour pour tous) donnait un monde où personne ne retient rien (environ 32 % à l'examen dans les deux ordres, écart nul) : ses valeurs de départ ont été alignées sur celles de A. Le scénario C a été ajouté ensuite ; des essais exploratoires de 300 élèves, avec un niveau de départ moyen de +1, +2 et +3, n'avaient pas montré d'écart net.
