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


# ── Synthesis Boundary Tests ─────────────────────────


def test_synthesis_uses_remote_openai_api() -> None:
    """Verify synthesis source references openai_api_key (remote API).

    The synthesis layer communicates with the remote OpenAI API,
    not the local vLLM server.
    """
    synthesis_dir = Path("src/synthesis")
    for py_file in synthesis_dir.rglob("*.py"):
        source = py_file.read_text()
        if "AsyncOpenAI" in source:
            assert "openai_api_key" in source, (
                f"src/synthesis/{py_file.name} uses AsyncOpenAI but does not "
                "reference openai_api_key — it must use the remote API"
            )


def test_synthesis_does_not_use_vllm() -> None:
    """Verify synthesis source does NOT reference vllm_base_url.

    The synthesis layer must not connect to the local vLLM server.
    """
    synthesis_dir = Path("src/synthesis")
    for py_file in synthesis_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "vllm_base_url" not in source, (
            f"src/synthesis/{py_file.name} must not reference vllm_base_url "
            "— it communicates with the remote OpenAI API only"
        )


def test_synthesis_does_not_import_engine() -> None:
    """Verify synthesis does not import from src.engine (layer violation).

    The synthesis layer sits above the engine layer in the dependency
    hierarchy, so it must not import from the engine.
    """
    synthesis_dir = Path("src/synthesis")
    for py_file in synthesis_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "from src.engine" not in source, (
            f"src/synthesis/{py_file.name} must not import from src.engine "
            "— synthesis sits above the engine layer"
        )
        assert "import src.engine" not in source, (
            f"src/synthesis/{py_file.name} must not import src.engine"
        )


# ── Scoring Boundary Tests ─────────────────────────


def test_scoring_uses_remote_openai_api() -> None:
    """Verify scoring source references openai_api_key (remote API).

    The scoring layer communicates with the remote OpenAI API,
    not the local vLLM server.
    """
    scoring_dir = Path("src/scoring")
    for py_file in scoring_dir.rglob("*.py"):
        source = py_file.read_text()
        if "AsyncOpenAI" in source:
            assert "openai_api_key" in source, (
                f"src/scoring/{py_file.name} uses AsyncOpenAI but does not "
                "reference openai_api_key — it must use the remote API"
            )


def test_scoring_does_not_use_vllm() -> None:
    """Verify scoring source does NOT reference vllm_base_url.

    The scoring layer must not connect to the local vLLM server.
    """
    scoring_dir = Path("src/scoring")
    for py_file in scoring_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "vllm_base_url" not in source, (
            f"src/scoring/{py_file.name} must not reference vllm_base_url "
            "— it communicates with the remote OpenAI API only"
        )


def test_scoring_does_not_import_engine() -> None:
    """Verify scoring does not import from src.engine (layer violation).

    The scoring layer sits above the engine layer in the dependency
    hierarchy, so it must not import from the engine.
    """
    scoring_dir = Path("src/scoring")
    for py_file in scoring_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "from src.engine" not in source, (
            f"src/scoring/{py_file.name} must not import from src.engine "
            "— scoring sits above the engine layer"
        )
        assert "import src.engine" not in source, (
            f"src/scoring/{py_file.name} must not import src.engine"
        )


def test_scoring_does_not_import_synthesis() -> None:
    """Verify scoring does not import from src.synthesis (layer violation).

    The scoring layer receives data from synthesis but must not import
    from it — it sits above synthesis in the dependency hierarchy.
    """
    scoring_dir = Path("src/scoring")
    for py_file in scoring_dir.rglob("*.py"):
        source = py_file.read_text()
        assert "from src.synthesis" not in source, (
            f"src/scoring/{py_file.name} must not import from src.synthesis "
            "— scoring receives data, not modules"
        )
        assert "import src.synthesis" not in source, (
            f"src/scoring/{py_file.name} must not import src.synthesis"
        )
