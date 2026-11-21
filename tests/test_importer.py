"""Tests de l'import de questions CSV et JSON (BF-10, BNF-02, BNF-04)."""

import json

import pytest

from src.data import repository
from src.logic import importer
from src.logic.auth import PermissionDeniedError

HEADER = "concept,difficulte,enonce,option_a,option_b,option_c,option_d,bonne_reponse,explication"


def line(n=1, **changes):
    """Une ligne CSV valide ; `changes` remplace certains champs (ex. difficulte="impossible")."""
    fields = {
        "concept": "MoSCoW", "difficulte": "moyen", "enonce": f"Question {n} ?",
        "option_a": "Un", "option_b": "Deux", "option_c": "Trois", "option_d": "Quatre",
        "bonne_reponse": "C", "explication": "Parce que.",
    }
    fields.update(changes)
    return ",".join(fields[name] for name in importer.CSV_COLUMNS)


def csv_file(*lines):
    return "\n".join([HEADER, *lines]) + "\n"


def json_item(n=1, **changes):
    item = {
        "concept": "MoSCoW", "difficulte": "moyen", "enonce": f"Question {n} ?",
        "options": ["Un", "Deux", "Trois", "Quatre"], "bonne_reponse": "C", "explication": "Parce que.",
    }
    item.update(changes)
    return item


# ---------- CSV valide ----------

def test_valid_csv_is_imported(conn, admin):
    """BF-10 : les questions valides sont importées, avec le bon indice de bonne réponse."""
    report = importer.import_questions(conn, admin, "Chapitre 1", csv_file(line(1), line(2)), "csv")
    assert report.imported == 2 and report.ok
    (chapter,) = repository.list_chapters(conn)
    assert (chapter.title, chapter.question_count) == ("Chapitre 1", 2)
    questions = repository.load_questions(conn, chapter.id)
    assert questions[0].correct_index == 2  # la lettre C
    assert questions[0].options == ("Un", "Deux", "Trois", "Quatre")


def test_semicolon_separated_csv_is_accepted(conn, admin):
    """BF-10 : un fichier enregistré par Excel en français (séparateur « ; ») est compris."""
    content = csv_file(line(1)).replace(",", ";")
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 1 and report.ok


def test_csv_starting_with_a_bom_is_accepted(conn, admin):
    """BF-10 : le caractère invisible ajouté par certains éditeurs au début du fichier est ignoré."""
    report = importer.import_questions(conn, admin, "Chapitre 1", "﻿" + csv_file(line(1)), "csv")
    assert report.imported == 1


def test_lowercase_answer_letter_and_uppercase_difficulty_are_accepted(conn, admin):
    """BF-10 : « b » et « DIFFICILE » sont normalisés."""
    content = csv_file(line(1, bonne_reponse="b", difficulte="DIFFICILE"))
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    (question,) = repository.load_questions(conn, repository.list_chapters(conn)[0].id)
    assert report.imported == 1
    assert (question.correct_index, question.difficulty) == (1, "difficile")


# ---------- CSV avec lignes invalides ----------

def test_invalid_line_is_rejected_with_its_number_and_valid_ones_are_kept(conn, admin):
    """BF-10 : une ligne invalide est rejetée avec son numéro, les autres sont importées."""
    content = csv_file(line(1), line(2, difficulte="impossible"), line(3))
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 2
    (error,) = report.rejected
    assert error.label == "Ligne 3"  # l'en-tête est la ligne 1
    assert "difficulté" in error.message
    assert str(error).startswith("Ligne 3 : ")
    assert not report.ok


def test_every_problem_of_a_line_is_reported(conn, admin):
    """BF-10 : si une ligne cumule plusieurs défauts, le message les liste tous."""
    content = csv_file(line(1, enonce="", bonne_reponse="Z", explication=""))
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    message = report.rejected[0].message
    assert "énoncé" in message and "bonne réponse" in message and "explication" in message


def test_identical_options_are_rejected(conn, admin):
    """BF-10 : quatre options doivent être différentes, sinon la question est ambiguë."""
    content = csv_file(line(1, option_b="un"))  # même texte que l'option A, sans tenir compte de la casse
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 0
    assert "différentes" in report.rejected[0].message


def test_empty_option_is_rejected(conn, admin):
    """BF-10 : une option vide est refusée."""
    report = importer.import_questions(conn, admin, "Chapitre 1", csv_file(line(1, option_d="")), "csv")
    assert report.imported == 0 and "4 options" in report.rejected[0].message


def test_short_line_is_rejected_without_crashing(conn, admin):
    """BNF-04 : une ligne à laquelle il manque des colonnes est rejetée proprement."""
    report = importer.import_questions(conn, admin, "Chapitre 1", csv_file("MoSCoW,facile,Question ?"), "csv")
    assert report.imported == 0 and len(report.rejected) == 1


def test_blank_lines_are_ignored(conn, admin):
    """BF-10 : les lignes vides ne comptent ni comme importées, ni comme rejetées."""
    content = HEADER + "\n\n" + line(1) + "\n\n\n" + line(2) + "\n"
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 2 and report.rejected == []


# ---------- Fichiers mal formés (BNF-04) ----------

def test_missing_columns_reject_the_whole_file(conn, admin):
    """BNF-04 : un en-tête incomplet fait refuser le fichier avec la liste des colonnes manquantes."""
    content = "concept,enonce\nMoSCoW,Question ?\n"
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 0
    assert "difficulte" in report.file_error and "bonne_reponse" in report.file_error
    assert repository.list_chapters(conn) == []


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_empty_file_is_refused_with_a_message(conn, admin, fmt):
    """BNF-04 : un fichier vide est refusé sans planter."""
    report = importer.import_questions(conn, admin, "Chapitre 1", "   \n", fmt)
    assert report.file_error is not None and report.imported == 0


def test_binary_garbage_does_not_crash(conn, admin):
    """BNF-04 : un fichier qui n'est pas du texte est refusé, l'application ne plante pas."""
    report = importer.import_questions(conn, admin, "Chapitre 1", "\x00\x01\x02\x03", "csv")
    assert report.imported == 0 and report.file_error is not None


def test_chapter_is_not_created_when_every_line_is_invalid(conn, admin):
    """BF-10 : si rien n'est importable, aucun chapitre vide n'est créé."""
    report = importer.import_questions(conn, admin, "Chapitre 1", csv_file(line(1, difficulte="x")), "csv")
    assert report.imported == 0 and len(report.rejected) == 1
    assert repository.list_chapters(conn) == []


def test_chapter_title_is_required(conn, admin):
    """BF-10 : sans titre de chapitre, l'import est refusé."""
    report = importer.import_questions(conn, admin, "   ", csv_file(line(1)), "csv")
    assert "titre" in report.file_error


def test_importing_the_same_file_twice_adds_nothing(conn, admin):
    """BF-10 : un second import du même fichier ne crée aucun doublon, et le dit."""
    content = csv_file(line(1), line(2))
    importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    second = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert second.imported == 0
    assert len(second.rejected) == 2 and "déjà présente" in second.rejected[0].message
    assert repository.list_chapters(conn)[0].question_count == 2


# ---------- JSON ----------

def test_valid_json_is_imported(conn, admin):
    """BF-10 : le format JSON est accepté comme le CSV."""
    content = json.dumps([json_item(1), json_item(2)])
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "json")
    assert report.imported == 2 and report.ok


def test_json_item_with_wrong_number_of_options_is_rejected(conn, admin):
    """BF-10 : une question JSON sans 4 options est rejetée avec son numéro."""
    content = json.dumps([json_item(1), json_item(2, options=["Un", "Deux", "Trois"])])
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "json")
    assert report.imported == 1
    assert report.rejected[0].label == "Question 2"


def test_json_item_that_is_not_an_object_is_rejected(conn, admin):
    """BNF-04 : un élément JSON qui n'est pas un objet est rejeté sans planter."""
    content = json.dumps([json_item(1), "une chaîne", 42])
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "json")
    assert report.imported == 1 and [e.label for e in report.rejected] == ["Question 2", "Question 3"]


def test_invalid_json_syntax_is_refused_with_a_message(conn, admin):
    """BNF-04 : du JSON cassé est refusé avec un message, sans planter."""
    report = importer.import_questions(conn, admin, "Chapitre 1", '[{"concept": ', "json")
    assert "JSON invalide" in report.file_error and report.imported == 0


def test_json_that_is_not_a_list_is_refused(conn, admin):
    """BNF-04 : un JSON qui n'est pas une liste de questions est refusé."""
    report = importer.import_questions(conn, admin, "Chapitre 1", json.dumps({"concept": "x"}), "json")
    assert "liste" in report.file_error


# ---------- Droits d'accès (BNF-02) ----------

def test_student_cannot_import_questions(conn, student):
    """BNF-02 : un étudiant qui tente d'importer est refusé, et rien n'est créé en base."""
    with pytest.raises(PermissionDeniedError):
        importer.import_questions(conn, student, "Chapitre 1", csv_file(line(1)), "csv")
    assert repository.list_chapters(conn) == []


def test_anonymous_visitor_cannot_import_questions(conn):
    """BNF-02 : sans connexion, l'import est refusé."""
    with pytest.raises(PermissionDeniedError):
        importer.import_questions(conn, None, "Chapitre 1", csv_file(line(1)), "csv")


# ---------- Utilitaires ----------

def test_decode_upload_handles_utf8_bom_and_excel_encoding():
    """BF-10 : les accents sont lus correctement qu'ils soient en UTF-8, avec BOM, ou en Windows-1252."""
    assert importer.decode_upload("Élicitation".encode("utf-8")) == "Élicitation"
    assert importer.decode_upload("﻿Élicitation".encode("utf-8")) == "Élicitation"
    assert importer.decode_upload("Élicitation".encode("cp1252")) == "Élicitation"


@pytest.mark.parametrize("name, expected", [("banque.csv", "csv"), ("BANQUE.JSON", "json")])
def test_format_is_detected_from_the_file_name(name, expected):
    """BF-10 : l'extension du fichier décide du format."""
    assert importer.detect_format(name) == expected


def test_unsupported_formats_are_refused():
    """BF-10 : un format inconnu est refusé avec une erreur claire."""
    with pytest.raises(ValueError):
        importer.detect_format("banque.pdf")
    with pytest.raises(ValueError):
        importer.parse_questions("<xml/>", "xml")


# ---------- Cas limites supplémentaires ----------

def test_missing_concept_and_too_long_fields_are_rejected(conn, admin):
    """BF-10 : un concept manquant, ou un concept / énoncé démesurés, font rejeter la ligne."""
    content = csv_file(
        line(1, concept=""),
        line(2, concept="C" * 101),
        line(3, enonce="E" * 1001),
    )
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    messages = [e.message for e in report.rejected]
    assert report.imported == 0
    assert "concept manquant" in messages[0]
    assert "concept trop long" in messages[1]
    assert "énoncé trop long" in messages[2]


def test_line_with_only_separators_is_ignored(conn, admin):
    """BF-10 : une ligne qui ne contient que des virgules est considérée comme vide."""
    content = csv_file(line(1), ",,,,,,,,", line(2))
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 2 and report.rejected == []


def test_empty_json_list_is_refused(conn, admin):
    """BNF-04 : une liste JSON vide est refusée avec un message."""
    report = importer.import_questions(conn, admin, "Chapitre 1", "[]", "json")
    assert "vide" in report.file_error


def test_json_item_with_an_invalid_field_is_rejected_with_its_number(conn, admin):
    """BF-10 : une question JSON dont un champ est invalide est rejetée, les autres passent."""
    content = json.dumps([json_item(1), json_item(2, difficulte="impossible"), json_item(3)])
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "json")
    assert report.imported == 2
    assert report.rejected[0].label == "Question 2" and "difficulté" in report.rejected[0].message


def test_oversized_csv_cell_does_not_crash(conn, admin):
    """BNF-04 : une cellule démesurée (fichier piégé) est refusée proprement."""
    content = csv_file(line(1, enonce="x" * 200_000))
    report = importer.import_questions(conn, admin, "Chapitre 1", content, "csv")
    assert report.imported == 0
    assert report.file_error is not None or report.rejected
