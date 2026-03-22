"""Architectural boundary verification tests.

These tests ensure that module boundaries defined in CLAUDE.md
are respected. They inspect source files for forbidden imports
to catch boundary violations at test time.
"""

import ast
from pathlib import Path


def _get_imports(file_path: Path) -> set[str]:
    """Extract all imported module names from a Python file."""
    source = file_path.read_text()
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def _get_all_imports_in_dir(dir_path: Path) -> set[str]:
    """Collect all imports from all Python files in a directory."""
    all_imports: set[str] = set()
    for py_file in dir_path.rglob("*.py"):
        all_imports.update(_get_imports(py_file))
    return all_imports


def test_engine_has_no_anthropic_imports() -> None:
    """Verify the engine module does not import the Anthropic SDK.

    The engine layer communicates with vLLM only — never the Anthropic API.
    """
    engine_dir = Path("src/engine")
    if not engine_dir.exists():
        return
    imports = _get_all_imports_in_dir(engine_dir)
    assert "anthropic" not in imports, (
        "src/engine/ must not import anthropic — it communicates with vLLM only"
    )


def test_personas_has_no_llm_imports() -> None:
    """Verify the persona module makes no LLM calls.

    The persona layer is pure data and selection logic.
    """
    personas_dir = Path("src/personas")
    if not personas_dir.exists():
        return
    imports = _get_all_imports_in_dir(personas_dir)
    assert "openai" not in imports, (
        "src/personas/ must not import openai — it is pure data"
    )
    assert "anthropic" not in imports, (
        "src/personas/ must not import anthropic — it is pure data"
    )


def test_db_has_no_llm_imports() -> None:
    """Verify the database module makes no LLM calls.

    The data layer handles storage only.
    """
    db_dir = Path("src/db")
    if not db_dir.exists():
        return
    imports = _get_all_imports_in_dir(db_dir)
    assert "openai" not in imports, (
        "src/db/ must not import openai — it handles storage only"
    )
    assert "anthropic" not in imports, (
        "src/db/ must not import anthropic — it handles storage only"
    )
