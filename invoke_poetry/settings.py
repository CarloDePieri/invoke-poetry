import subprocess
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterable, Optional

from invoke import Runner
from invoke.runners import Result

from invoke_poetry.utils import look_for_poetry_env_file


def _install_project_dependencies_default_hook(c: Runner, quiet: bool = True) -> Result:
    """The default hook for installing project dependencies: it will simply run 'poetry install'."""
    return c.run("poetry install", hide=quiet, pty=True)


class Settings:
    """TODO"""

    install_project_dependencies_hook: ClassVar[
        Callable[..., Any]
    ] = _install_project_dependencies_default_hook
    poetry_env_file: ClassVar[Optional[Path]]
    default_python_version: ClassVar[str]
    supported_python_versions: ClassVar[Iterable[str]]

    @staticmethod
    def init(
        default_python_version: str,
        supported_python_versions: Iterable[str],
        install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
        poetry_env_file: Optional[Path] = None,
    ) -> None:
        Settings.default_python_version = default_python_version
        Settings.supported_python_versions = supported_python_versions

        if install_project_dependencies_hook:
            Settings.install_project_dependencies_hook = (
                install_project_dependencies_hook
            )

        Settings.poetry_env_file = None
        if poetry_env_file:
            if poetry_env_file.is_file():
                Settings.poetry_env_file = poetry_env_file
        else:
            # Try to look for it
            try:
                # search for the root of the project
                env_file = look_for_poetry_env_file()
                if env_file:
                    Settings.poetry_env_file = env_file
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
