"""Tests d'architecture : les trois couches restent séparées et le code est documenté (BNF-05)."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def python_files(folder):
    return sorted(p for p in (SRC / folder).rglob("*.py") if p.name != "__init__.py")


def source(path):
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", python_files("ui"), ids=lambda p: p.name)
def test_ui_files_never_touch_the_database(path):
    """BNF-05 : aucun fichier d'interface n'accède à la base (ni SQL, ni couche données) : tout passe par la logique."""
    text = source(path)
    assert "src.data" not in text and "sqlite3" not in text
    assert "SELECT " not in text and "INSERT " not in text


@pytest.mark.parametrize("path", python_files("logic") + python_files("data"), ids=lambda p: p.name)
def test_logic_and_data_layers_do_not_depend_on_the_interface(path):
    """BNF-05 : la logique et les données ne connaissent ni Streamlit ni l'interface (donc testables seules)."""
    text = source(path)
    assert "streamlit" not in text and "src.ui" not in text


@pytest.mark.parametrize("path", python_files("logic"), ids=lambda p: p.name)
def test_game_rules_live_in_the_logic_layer_only(path):
    """BNF-05 : la logique n'écrit pas de SQL elle-même, elle passe par `repository`."""
    text = source(path)
    assert "sqlite3.connect" not in text and "SELECT " not in text and "INSERT " not in text


def test_every_public_function_and_class_has_a_docstring():
    """BNF-05 : chaque fonction, classe et méthode publique possède une docstring."""
    missing = []
    files = python_files("ui") + python_files("logic") + python_files("data") + [SRC / "config.py"]
    files += [ROOT / "app.py", ROOT / "init_db.py"]
    for path in files:
        tree = ast.parse(source(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if ast.get_docstring(node) is None:
                    missing.append(f"{path.name}:{node.lineno} {node.name}")
        if ast.get_docstring(tree) is None:
            missing.append(f"{path.name}: docstring de module")
    assert missing == [], "Docstrings manquantes : " + ", ".join(missing)
