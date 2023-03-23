from pathlib import Path
from typing import Any, Callable, ClassVar, Iterable, Optional

from invoke import Runner
from invoke.runners import Result


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
    venv_link_path = Path(".venv")

    @staticmethod
    def init(
        default_python_version: str,
        supported_python_versions: Iterable[str],
        install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
    ) -> None:
        Settings.default_python_version = default_python_version
        Settings.supported_python_versions = supported_python_versions

        if install_project_dependencies_hook:
            Settings.install_project_dependencies_hook = (
                install_project_dependencies_hook
            )
