"""Tests de la matrice de traçabilité : chaque exigence est reliée à des tests, et la matrice est à jour."""

from tools import rtm


def test_every_automated_requirement_has_at_least_one_test():
    """BNF-05 : aucune exigence vérifiée automatiquement n'est sans test (pas de fonctionnalité orpheline)."""
    by_requirement, _ = rtm.collect_tests()
    for requirement in rtm.REQUIREMENTS:
        if requirement.verification in ("auto", "mixte"):
            assert by_requirement.get(requirement.ident), f"{requirement.ident} n'a aucun test rattaché"


def test_tests_only_cite_requirements_that_exist():
    """BNF-05 : un identifiant de test (BF-xx, BNF-xx) qui n'existe pas dans le cahier des charges est une faute de frappe."""
    by_requirement, _ = rtm.collect_tests()
    assert set(by_requirement) <= rtm.KNOWN_IDS


def test_manual_and_unimplemented_requirements_are_declared_as_such():
    """BNF-05 : ce qui n'est pas automatisé est écrit noir sur blanc dans la matrice, jamais caché."""
    by_requirement, _ = rtm.collect_tests()
    markdown = rtm.build_markdown(by_requirement, [])
    assert "Non réalisé" in markdown and "Test manuel" in markdown


def test_generated_matrix_files_are_up_to_date():
    """BNF-05 : les fichiers de docs/ correspondent aux tests actuels ; sinon, relancer  python -m tools.rtm."""
    by_requirement, untagged = rtm.collect_tests()
    markdown_file = rtm.DOCS_DIR / "matrice_tracabilite.md"
    latex_file = rtm.DOCS_DIR / "matrice_tracabilite.tex"
    assert markdown_file.read_text(encoding="utf-8") == rtm.build_markdown(by_requirement, untagged), (
        "docs/matrice_tracabilite.md est périmé : lance  python -m tools.rtm"
    )
    assert latex_file.read_text(encoding="utf-8") == rtm.build_latex(by_requirement, untagged), (
        "docs/matrice_tracabilite.tex est périmé : lance  python -m tools.rtm"
    )
