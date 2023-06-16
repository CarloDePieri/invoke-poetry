from pathlib import Path
from typing import Any, Callable, ClassVar, Iterable, Optional

from invoke import Context, Result  # type: ignore[attr-defined]


class Settings:
    """Module-wide settings storage."""

    install_project_dependencies_hook: ClassVar[Callable[..., Any]]
    default_python_version: ClassVar[str]
    supported_python_versions: ClassVar[Iterable[str]]
    venv_link_path: ClassVar[Path]
    poetry_bin: ClassVar[str]

    @staticmethod
    def init(
        default_python_version: str,
        supported_python_versions: Iterable[str],
        install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
        poetry_bin: Optional[str] = None,
        venv_link_path: Optional[str] = None,
    ) -> None:
        Settings.default_python_version = default_python_version
        Settings.supported_python_versions = supported_python_versions

        Settings.poetry_bin = poetry_bin if poetry_bin else "poetry"
        Settings.venv_link_path = (
            Path(venv_link_path) if venv_link_path else Path(".venv")
        )

        if install_project_dependencies_hook:
            Settings.install_project_dependencies_hook = (
                install_project_dependencies_hook
            )
        else:
            Settings.install_project_dependencies_hook = (
                Settings._install_project_dependencies_default_hook
            )

    @staticmethod
    def _install_project_dependencies_default_hook(
        c: Context, quiet: bool = True
    ) -> Optional[Result]:
        """The default hook for installing project dependencies: it will simply run 'poetry install'."""
        return c.run(Settings.poetry_bin + " install", hide=quiet, pty=True)
