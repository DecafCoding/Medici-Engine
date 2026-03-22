"""Architectural boundary verification tests.

These tests ensure that module boundaries defined in CLAUDE.md
are respected. They inspect source files for forbidden imports
and usage patterns to catch boundary violations at test time.
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


def test_engine_does_not_use_remote_openai_api() -> None:
    """Verify the engine module only uses vLLM, not the remote OpenAI API.

    Both engine and synthesis/scoring use the openai SDK, but engine must
    only connect to the local vLLM server. We verify by checking that engine
    source never references openai_api_key (the remote API credential).
    """
    engine_dir = Path("src/engine")
    if not engine_dir.exists():
        return
    for py_file in engine_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "openai_api_key" not in source, (
            f"src/engine/{py_file.name} must not reference openai_api_key "
            "— it communicates with vLLM only"
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
