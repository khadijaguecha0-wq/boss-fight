"""Génère la matrice de traçabilité (RTM) : exigence -> cas d'utilisation -> modules -> tests.

Les liens exigence -> tests ne sont pas écrits à la main : ils sont lus dans les docstrings des
tests (chaque test cite l'identifiant BF-xx ou BNF-xx qu'il vérifie). La matrice est donc toujours
à jour : il suffit de relancer  python -m tools.rtm

Sorties : docs/matrice_tracabilite.md (lecture) et docs/matrice_tracabilite.tex (rapport LaTeX).
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"
DOCS_DIR = ROOT / "docs"
ID_PATTERN = re.compile(r"\b(BNF-\d{2}|BF-\d{2})\b")

# Vérification : "auto" = tests automatisés, "mixte" = automatisés + test manuel, "manuel", "non réalisé".
@dataclass(frozen=True)
class Requirement:
    """Une exigence du cahier des charges et la façon dont elle est vérifiée."""

    ident: str
    title: str
    priority: str
    use_case: str
    modules: tuple
    verification: str
    note: str = ""


REQUIREMENTS = [
    Requirement("BF-01", "Créer un compte", "Must", "UC-01",
                ("logic/auth.py", "data/repository.py", "ui/auth_page.py"), "auto"),
    Requirement("BF-02", "Se connecter et se déconnecter", "Must", "UC-02",
                ("logic/auth.py", "ui/auth_page.py", "ui/state.py", "ui/sidebar.py"), "auto"),
    Requirement("BF-03", "Choisir un chapitre", "Must", "UC-03",
                ("logic/game_service.py", "data/repository.py", "ui/dashboard_page.py"), "auto"),
    Requirement("BF-04", "Répondre aux questions et combattre le boss", "Must", "UC-04",
                ("logic/battle.py", "logic/game_service.py", "ui/battle_page.py"), "auto"),
    Requirement("BF-05", "Correction et explication après chaque réponse", "Must", "UC-04",
                ("logic/battle.py", "ui/battle_page.py"), "auto"),
    Requirement("BF-06", "Questions choisies selon le niveau et le risque d'oubli", "Must", "UC-04",
                ("logic/memory_model.py", "logic/selector.py", "logic/game_service.py"), "auto"),
    Requirement("BF-07", "Résultat du combat et concepts à revoir", "Must", "UC-04",
                ("logic/battle.py", "logic/game_service.py", "ui/result_page.py"), "auto"),
    Requirement("BF-08", "Maîtrise par concept", "Must", "UC-05",
                ("logic/memory_model.py", "logic/game_service.py", "ui/dashboard_page.py"), "auto"),
    Requirement("BF-09", "Évolution de la maîtrise dans le temps", "Should", "UC-06",
                ("logic/game_service.py", "data/repository.py", "ui/progress_page.py"), "auto"),
    Requirement("BF-10", "Importer une banque de questions", "Must", "UC-07",
                ("logic/importer.py", "logic/bootstrap.py", "ui/import_page.py"), "auto"),
    Requirement("BF-11", "Modifier ou supprimer des questions", "Could", "UC-08", (), "non réalisé",
                "Hors périmètre de cette version (priorité Could)."),
    Requirement("BNF-01", "Performance", "Must", "-",
                ("logic/selector.py", "data/repository.py"), "auto",
                "Mesure sur la logique et la base, hors affichage Streamlit."),
    Requirement("BNF-02", "Sécurité", "Must", "-",
                ("logic/auth.py", "data/repository.py", "logic/importer.py"), "auto"),
    Requirement("BNF-03", "Usabilité", "Should", "-", ("ui/",), "manuel",
                "Test avec 3 camarades (voir plan de recette)."),
    Requirement("BNF-04", "Fiabilité", "Must", "-",
                ("data/repository.py", "logic/importer.py", "logic/game_service.py"), "auto"),
    Requirement("BNF-05", "Maintenabilité", "Must", "-",
                ("src/ (3 couches)",), "mixte",
                "Rapport de couverture pytest-cov à joindre au rapport."),
    Requirement("BNF-06", "Portabilité", "Should", "-", (), "manuel",
                "Test manuel sur Chrome et Firefox, application en ligne."),
    Requirement("BNF-07", "Disponibilité", "Should", "-", (), "manuel",
                "Vérification avant la présentation."),
    Requirement("BNF-08", "Exactitude du modèle d'adaptation", "Must", "-",
                ("logic/memory_model.py", "logic/selector.py"), "mixte",
                "Tests unitaires ; la simulation contre un ordre aléatoire est un livrable à part."),
]
KNOWN_IDS = {r.ident for r in REQUIREMENTS}


@dataclass(frozen=True)
class TestRef:
    """Référence d'un test : fichier et nom de la fonction."""

    __test__ = False  # pytest ne doit pas essayer de collecter cette classe
    file: str
    name: str


def collect_tests(tests_dir: Path = TESTS_DIR):
    """Lit les tests et renvoie (tests par exigence, tests sans exigence citée)."""
    by_requirement = defaultdict(list)
    untagged = []
    for path in sorted(tests_dir.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                ref = TestRef(path.name, node.name)
                ids = sorted(set(ID_PATTERN.findall(ast.get_docstring(node) or "")))
                if not ids:
                    untagged.append(ref)
                for ident in ids:
                    by_requirement[ident].append(ref)
    return by_requirement, untagged


def _status(requirement: Requirement, count: int) -> str:
    if requirement.verification == "non réalisé":
        return "Non réalisé"
    if requirement.verification == "manuel":
        return "Test manuel"
    plural = "s" if count > 1 else ""
    if requirement.verification == "mixte":
        return f"{count} test{plural} + vérification complémentaire"
    return f"{count} test{plural} automatisé{plural}"


# ---------- Markdown ----------

def build_markdown(by_requirement, untagged) -> str:
    total = sum(len({(t.file, t.name) for t in refs}) for refs in by_requirement.values())
    lines = [
        "# Matrice de traçabilité des exigences (RTM)",
        "",
        "Générée automatiquement par `python -m tools.rtm` à partir des docstrings des tests.",
        "Un test paramétré (plusieurs cas) compte pour une seule fonction de test.",
        "",
        "| Exigence | Prio. | Cas d'util. | Modules | Vérification |",
        "|---|---|---|---|---|",
    ]
    for r in REQUIREMENTS:
        count = len(by_requirement.get(r.ident, []))
        modules = ", ".join(f"`{m}`" for m in r.modules) or "-"
        lines.append(f"| **{r.ident}** {r.title} | {r.priority} | {r.use_case} | {modules} | {_status(r, count)} |")
    lines += ["", "Remarques :"]
    lines += [f"- **{r.ident}** : {r.note}" for r in REQUIREMENTS if r.note]
    lines += ["", f"Tests rattachés à au moins une exigence : {total} ; tests complémentaires (robustesse, "
              f"modèle de données) : {len(untagged)}.", "", "## Détail : tests par exigence", ""]
    for r in REQUIREMENTS:
        refs = by_requirement.get(r.ident, [])
        lines.append(f"### {r.ident} {r.title}")
        if not refs:
            lines.append(f"_Aucun test automatisé ({_status(r, 0).lower()})._")
        for ref in refs:
            lines.append(f"- `{ref.file}::{ref.name}`")
        lines.append("")
    return "\n".join(lines)


# ---------- LaTeX ----------

_ACCENTS = {
    "é": r"\'e", "è": r"\`e", "ê": r"\^e", "ë": r'\"e', "à": r"\`a", "â": r"\^a", "î": r"\^\i{}",
    "ï": r'\"\i{}', "ô": r"\^o", "ù": r"\`u", "û": r"\^u", "ç": r"\c{c}", "œ": r"\oe{}",
    "É": r"\'E", "È": r"\`E", "À": r"\`A", "Ç": r"\c{C}", "’": "'", "«": r"\og{}", "»": r"\fg{}",
}


def tex(text: str) -> str:
    """Rend un texte sûr pour LaTeX (caractères spéciaux et accents)."""
    text = text.replace("\\", r"\textbackslash{}")
    for char, replacement in {"&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#", "$": r"\$"}.items():
        text = text.replace(char, replacement)
    return "".join(_ACCENTS.get(c, c) for c in text)


def build_latex(by_requirement, untagged) -> str:
    rows = []
    for r in REQUIREMENTS:
        count = len(by_requirement.get(r.ident, []))
        modules = r"\newline ".join(tex(m) for m in r.modules) or "-"
        rows.append(
            f"{tex(r.ident)} {tex(r.title)} & {tex(r.priority)} & {tex(r.use_case)} & {modules} & {tex(_status(r, count))}\\\\\n\\addlinespace"
        )
    body = "\n".join(rows)
    return (
        "% Généré par `python -m tools.rtm` : ne pas modifier à la main.\n"
        "% Nécessite les packages longtable, booktabs et array dans le préambule.\n"
        "{\\small\n"
        "\\begin{longtable}{>{\\raggedright\\arraybackslash}p{4.0cm}p{1.0cm}p{1.2cm}"
        ">{\\raggedright\\arraybackslash}p{4.6cm}>{\\raggedright\\arraybackslash}p{3.0cm}}\n"
        "\\toprule\n"
        "\\textbf{Exigence} & \\textbf{Prio.} & \\textbf{Cas d'util.} & \\textbf{Modules} & \\textbf{Vérification}\\\\\n"
        "\\midrule\n\\endhead\n"
        f"{body}\n"
        "\\bottomrule\n"
        "\\end{longtable}\n"
        "}\n"
    )


def main() -> None:
    """Écrit les deux fichiers de la matrice dans `docs/`."""
    by_requirement, untagged = collect_tests()
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "matrice_tracabilite.md").write_text(build_markdown(by_requirement, untagged), encoding="utf-8")
    (DOCS_DIR / "matrice_tracabilite.tex").write_text(build_latex(by_requirement, untagged), encoding="utf-8")
    print("Matrice écrite dans docs/matrice_tracabilite.md et docs/matrice_tracabilite.tex")
    for r in REQUIREMENTS:
        print(f"  {r.ident:7s} {_status(r, len(by_requirement.get(r.ident, [])))}")
    print(f"  tests complémentaires sans exigence citée : {len(untagged)}")


if __name__ == "__main__":
    main()
