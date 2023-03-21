from typing import Any, Callable, Iterable, Optional, cast

from invoke import Runner
from invoke.runners import Result

from invoke_poetry.logs import error


def _install_project_dependencies_default_hook(c: Runner, quiet: bool = True) -> Result:
    """The default hook for installing project dependencies: it will simply run 'poetry install'."""
    return c.run("poetry install", hide=quiet, pty=True)


class Settings:
    """TODO"""

    install_project_dependencies_hook: Callable[
        ..., Any
    ] = _install_project_dependencies_default_hook
    _default_python_version: Optional[str] = None
    _supported_python_versions: Optional[Iterable[str]] = None

    @staticmethod
    def init(
        default_python_version: str,
        supported_python_versions: Iterable[str],
        install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
    ) -> None:
        Settings._default_python_version = default_python_version
        Settings._supported_python_versions = supported_python_versions

        if install_project_dependencies_hook:
            Settings.install_project_dependencies_hook = (
                install_project_dependencies_hook
            )

    @property
    def default_python_version(self) -> str:
        """TODO"""
        if not self._default_python_version:
            self.exit_with_configuration_error("default_python_version")
        version = cast(
            str, self._default_python_version
        )  # This should be a string at this point
        return version

    @property
    def supported_python_versions(self) -> Iterable[str]:
        """TODO"""
        if not self._supported_python_versions:
            self.exit_with_configuration_error("supported_python_versions")
        versions = cast(
            Iterable[str], self._supported_python_versions
        )  # This should be strings at this point
        return versions

    @staticmethod
    def exit_with_configuration_error(missing_config: str) -> None:
        """TODO"""
        error("CONFIGURATION ERROR", exit_now=False)
        print(
            "\n\tRead invoke_poetry documentation!\n\n"
            f"\tYou need to set {missing_config} in your tasks file.\n"
        )
        error("CONFIGURATION ERROR")
