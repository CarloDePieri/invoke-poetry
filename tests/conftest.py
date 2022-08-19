import sys
from pathlib import Path
from typing import Callable

import pytest

pytest_plugins = "pytester"


@pytest.fixture
def inv() -> Path:
    interpreter = Path(sys.executable)
    return interpreter.parent / "inv"


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
    python = "^3.7"
    isort = "^5.10.1"
    
    [tool.poetry.dev-dependencies]
    
    [build-system]
    requires = ["poetry-core>=1.0.0"]
    build-backend = "poetry.core.masonry.api"
    """,
    )
    return pytester


@pytest.fixture
def debug() -> Callable[[bool], str]:
    def wrapper(start: bool = True) -> str:
        if start:
            debugger_code = (
                "\timport pydevd_pycharm;pydevd_pycharm.settrace('localhost', port=9000, "
                "stdoutToServer=True, stderrToServer=True)"
            )
        else:
            debugger_code = ""
        return debugger_code

    return wrapper
