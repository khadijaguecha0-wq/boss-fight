"""Import d'une banque de questions au format CSV ou JSON (BF-10, BNF-04).

Format attendu pour chaque question :
  concept, difficulte (facile / moyen / difficile), enonce, 4 options,
  bonne_reponse (A, B, C ou D), explication.

- CSV : une ligne d'en-tête  concept,difficulte,enonce,option_a,option_b,option_c,option_d,bonne_reponse,explication
  (la virgule ou le point-virgule sont acceptés comme séparateur).
- JSON : une liste d'objets avec les clés  concept, difficulte, enonce, options (liste de 4 textes),
  bonne_reponse, explication.

Une ligne invalide est rejetée avec son numéro ; les lignes valides sont importées quand même.
Un fichier mal formé est refusé en entier avec un message, sans faire planter l'application.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from dataclasses import dataclass, field

from src.config import DIFFICULTY_VALUE
from src.data import repository
from src.logic.auth import require_admin
from src.logic.models import User

CSV_COLUMNS = (
    "concept", "difficulte", "enonce",
    "option_a", "option_b", "option_c", "option_d",
    "bonne_reponse", "explication",
)
LETTERS = "ABCD"

# Modèle de fichier CSV proposé en téléchargement à l'administrateur (une question d'exemple).
CSV_TEMPLATE = (
    ",".join(CSV_COLUMNS) + "\n"
    "Priorisation MoSCoW,facile,Que signifie « Must have » ?,"
    "Vital pour le lancement,Confort si le temps le permet,Hors périmètre,Solution de contournement,"
    "A,Must have = indispensable à cette version.\n"
)
MAX_CONCEPT_LENGTH = 100
MAX_TEXT_LENGTH = 1000


@dataclass(frozen=True)
class QuestionRow:
    """Une question lue dans un fichier et déjà validée."""

    concept: str
    difficulty: str
    text: str
    options: tuple
    correct_index: int
    explanation: str


@dataclass(frozen=True)
class RowError:
    """Une ligne (ou une question) rejetée, avec la raison."""

    label: str      # « Ligne 7 » (CSV) ou « Question 3 » (JSON)
    message: str

    def __str__(self) -> str:
        return f"{self.label} : {self.message}"


@dataclass
class ImportReport:
    """Résultat d'un import, à afficher à l'administrateur."""

    imported: int = 0
    rejected: list = field(default_factory=list)   # liste de RowError
    file_error: str | None = None                  # problème qui concerne tout le fichier

    @property
    def ok(self) -> bool:
        """Vrai si le fichier a été lu sans erreur de fichier ni ligne rejetée."""
        return self.file_error is None and not self.rejected


# ---------- Lecture du fichier ----------

def decode_upload(raw: bytes) -> str:
    """Transforme les octets d'un fichier téléversé en texte (UTF-8, sinon Windows-1252 d'Excel)."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def detect_format(filename: str) -> str:
    """Déduit le format (« csv » ou « json ») à partir de l'extension du fichier."""
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return "csv"
    if lowered.endswith(".json"):
        return "json"
    raise ValueError("Format non pris en charge : utilise un fichier .csv ou .json.")


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def validate_row(raw: dict) -> QuestionRow:
    """Valide une question brute (dictionnaire). Lève `ValueError` en listant tous les problèmes."""
    problems = []

    concept = _clean(raw.get("concept"))
    if not concept:
        problems.append("concept manquant")
    elif len(concept) > MAX_CONCEPT_LENGTH:
        problems.append(f"concept trop long (plus de {MAX_CONCEPT_LENGTH} caractères)")

    difficulty = _clean(raw.get("difficulte")).lower()
    if difficulty not in DIFFICULTY_VALUE:
        problems.append("difficulté inconnue (attendu : facile, moyen ou difficile)")

    text = _clean(raw.get("enonce"))
    if not text:
        problems.append("énoncé manquant")
    elif len(text) > MAX_TEXT_LENGTH:
        problems.append(f"énoncé trop long (plus de {MAX_TEXT_LENGTH} caractères)")

    options = tuple(_clean(raw.get(f"option_{letter.lower()}")) for letter in LETTERS)
    if not all(options):
        problems.append("il faut exactement 4 options non vides")
    elif len({option.lower() for option in options}) < 4:
        problems.append("les 4 options doivent être différentes")

    answer = _clean(raw.get("bonne_reponse")).upper()
    if answer not in tuple(LETTERS):
        problems.append("bonne réponse invalide (attendu : A, B, C ou D)")

    explanation = _clean(raw.get("explication"))
    if not explanation:
        problems.append("explication manquante")

    if problems:
        raise ValueError("; ".join(problems))
    return QuestionRow(concept, difficulty, text, options, LETTERS.index(answer), explanation)


def _parse_csv(content: str):
    lines = [line for line in content.splitlines() if line.strip()]
    if not lines:
        return [], [], "Le fichier est vide."
    header = lines[0]
    delimiter = ";" if header.count(";") > header.count(",") else ","

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    columns = [(name or "").strip().lstrip("\ufeff").strip().lower() for name in (reader.fieldnames or [])]
    missing = [name for name in CSV_COLUMNS if name not in columns]
    if missing:
        return [], [], "Colonnes manquantes : " + ", ".join(missing) + "."
    reader.fieldnames = columns

    rows, errors = [], []
    try:
        for record in reader:
            label = f"Ligne {reader.line_num}"
            if not any(_clean(value) for key, value in record.items() if key is not None):
                continue
            try:
                rows.append((label, validate_row(record)))
            except ValueError as error:
                errors.append(RowError(label, str(error)))
    except csv.Error as error:
        return [], [], f"Fichier CSV illisible : {error}"
    return rows, errors, None


def _parse_json(content: str):
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        return [], [], f"Fichier JSON invalide : {error.msg} (ligne {error.lineno})."
    if not isinstance(data, list):
        return [], [], "Le fichier JSON doit contenir une liste de questions."
    if not data:
        return [], [], "Le fichier est vide."

    rows, errors = [], []
    for number, item in enumerate(data, start=1):
        label = f"Question {number}"
        if not isinstance(item, dict):
            errors.append(RowError(label, "ce n'est pas un objet JSON"))
            continue
        options = item.get("options")
        if not isinstance(options, list) or len(options) != 4:
            errors.append(RowError(label, "« options » doit être une liste de 4 textes"))
            continue
        record = dict(item)
        for letter, option in zip(LETTERS, options):
            record[f"option_{letter.lower()}"] = option
        try:
            rows.append((label, validate_row(record)))
        except ValueError as error:
            errors.append(RowError(label, str(error)))
    return rows, errors, None


def parse_questions(content: str, fmt: str):
    """Lit et valide un fichier. Renvoie (questions valides avec leur étiquette, erreurs, erreur de fichier)."""
    if fmt == "csv":
        return _parse_csv(content)
    if fmt == "json":
        return _parse_json(content)
    raise ValueError("Format non pris en charge : utilise « csv » ou « json ».")


# ---------- Import en base ----------

def import_questions(
    conn: sqlite3.Connection, user: User | None, chapter_title: str, content: str, fmt: str
) -> ImportReport:
    """Importe les questions valides d'un fichier dans un chapitre (BF-10).

    Réservé à l'administrateur : lève `PermissionDeniedError` pour tout autre utilisateur (BNF-02).
    """
    require_admin(user)

    chapter_title = chapter_title.strip()
    if not chapter_title:
        return ImportReport(file_error="Le titre du chapitre est obligatoire.")

    rows, errors, file_error = parse_questions(content, fmt)
    report = ImportReport(rejected=list(errors), file_error=file_error)
    if file_error or not rows:
        return report

    chapter_id = repository.get_or_create_chapter(conn, chapter_title)
    for label, row in rows:
        try:
            repository.add_question(
                conn, chapter_id, row.concept, row.text, row.options,
                row.correct_index, row.difficulty, row.explanation,
            )
            report.imported += 1
        except repository.DuplicateQuestionError:
            report.rejected.append(RowError(label, "question déjà présente pour ce concept"))
    return report
