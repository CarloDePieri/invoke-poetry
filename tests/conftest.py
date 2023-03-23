import sys
import textwrap
from pathlib import Path
from typing import Tuple

import pytest

pytest_plugins = "pytester"


@pytest.fixture
def venv_interpreter() -> Path:
    """Return the absolute path of the current interpreter."""
    interpreter = Path(sys.executable)
    return interpreter.absolute()


@pytest.fixture
def inv_bin(venv_interpreter) -> Tuple[Path, Path]:
    """Return a Tuple containing the interpreter and the invoke binary."""
    return venv_interpreter, venv_interpreter.parent.absolute() / "invoke"


@pytest.fixture
def poetry_bin(venv_interpreter) -> Tuple[Path, Path]:
    """Since poetry is installed in the venv and tries internally to use a relative path we need to use the external
    poetry bin during our tests.

    See: https://github.com/python-poetry/poetry/issues/2871"""
    return venv_interpreter, venv_interpreter.parent.absolute() / "poetry"


@pytest.fixture
def poetry_bin_str(poetry_bin) -> str:
    """Return a string in the form of 'interpreter poetry_bin'."""
    return f"{poetry_bin[0]} {poetry_bin[1]}"


@pytest.fixture
def pytester(pytester):
    pytester.makefile(
        ".toml", poetry="[virtualenvs]\nin-project = false\npath = '.venvs'"
    )

    pytester.makefile(
        ".toml",
        pyproject="""
    [tool.poetry]
    name = "test"
    version = "0.1.0"
    description = ""
    authors = ["Carlo De Pieri <depieri.carlo@gmail.com>"]
    
    [tool.poetry.dependencies]
    python = "^3.8"
    
    [tool.poetry.dev-dependencies]
    
    [build-system]
    requires = ["poetry-core>=1.0.0"]
    build-backend = "poetry.core.masonry.api"
    """,
    )
    return pytester


@pytest.fixture
def connect_debugger():
    def wrapper() -> str:
        return (
            "import pydevd_pycharm;pydevd_pycharm.settrace('localhost', port=9000, "
            "stdoutToServer=True, stderrToServer=True)\n"
        )

    return wrapper


@pytest.fixture()
def add_test_file(pytester, connect_debugger):
    def _add_test_file(test_source: str, debug_mode: bool = False) -> None:
        test_source = textwrap.dedent(test_source)
        if debug_mode:
            test_source = connect_debugger() + test_source
        pytester.makepyfile(tasks=test_source)

    return _add_test_file
