-- Schéma de la base SQLite de Boss Fight (modèle relationnel issu du diagramme de classes).
-- Toutes les tables sont créées seulement si elles n'existent pas (le script peut être relancé).

-- Comptes. Le pseudo est unique sans tenir compte des majuscules (COLLATE NOCASE).
-- Le mot de passe n'est jamais stocké en clair : seulement son hachage salé (BNF-02).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'etudiant' CHECK (role IN ('etudiant', 'admin')),
    created_at    TEXT NOT NULL
);

-- Un chapitre de cours = un boss.
CREATE TABLE IF NOT EXISTS chapters (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE
);

-- Un concept est une notion à retenir dans un chapitre (c'est lui qu'on oublie ou qu'on maîtrise).
CREATE TABLE IF NOT EXISTS concepts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    name       TEXT NOT NULL,
    UNIQUE (chapter_id, name)
);

-- Une question à 4 options ; correct_index vaut 0, 1, 2 ou 3 (A, B, C, D).
CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id    INTEGER NOT NULL REFERENCES concepts(id),
    text          TEXT NOT NULL,
    option_a      TEXT NOT NULL,
    option_b      TEXT NOT NULL,
    option_c      TEXT NOT NULL,
    option_d      TEXT NOT NULL,
    correct_index INTEGER NOT NULL CHECK (correct_index BETWEEN 0 AND 3),
    difficulty    TEXT NOT NULL CHECK (difficulty IN ('facile', 'moyen', 'difficile')),
    explanation   TEXT NOT NULL,
    UNIQUE (concept_id, text)
);

-- Maîtrise d'un concept par un étudiant : niveau (theta), stabilité de la mémoire et date de révision.
CREATE TABLE IF NOT EXISTS mastery (
    user_id     INTEGER NOT NULL REFERENCES users(id),
    concept_id  INTEGER NOT NULL REFERENCES concepts(id),
    theta       REAL NOT NULL,
    stability   REAL NOT NULL CHECK (stability > 0),
    last_review TEXT,
    PRIMARY KEY (user_id, concept_id)
);

-- Un combat d'un étudiant contre le boss d'un chapitre.
CREATE TABLE IF NOT EXISTS battles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    chapter_id     INTEGER NOT NULL REFERENCES chapters(id),
    started_at     TEXT NOT NULL,
    ended_at       TEXT,
    status         TEXT NOT NULL DEFAULT 'en_cours' CHECK (status IN ('en_cours', 'victoire', 'defaite')),
    boss_hp        INTEGER,
    lives          INTEGER,
    correct_count  INTEGER NOT NULL DEFAULT 0,
    answered_count INTEGER NOT NULL DEFAULT 0,
    mean_mastery   REAL            -- maîtrise moyenne en fin de combat, pour la courbe de progression (BF-09)
);

-- Historique des réponses données pendant un combat.
CREATE TABLE IF NOT EXISTS answers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    battle_id    INTEGER NOT NULL REFERENCES battles(id),
    question_id  INTEGER NOT NULL REFERENCES questions(id),
    chosen_index INTEGER NOT NULL CHECK (chosen_index BETWEEN 0 AND 3),
    is_correct   INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    answered_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_questions_concept ON questions(concept_id);
CREATE INDEX IF NOT EXISTS idx_answers_battle    ON answers(battle_id);
CREATE INDEX IF NOT EXISTS idx_battles_user      ON battles(user_id, started_at);
