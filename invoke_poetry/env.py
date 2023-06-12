import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional

from invoke import Runner  # type: ignore[attr-defined]

from invoke_poetry.collection import PatchedInvokeCollection
from invoke_poetry.logs import Colors, error, info, ok, warn
from invoke_poetry.poetry_api import PoetryAPI
from invoke_poetry.settings import Settings
from invoke_poetry.utils import delay_keyboard_interrupt, natural_sort_key

#
# ENV OPERATIONS
#


def env_activate(python_version: str, link: bool = True) -> None:
    """Activate a poetry env, creating the convenience symlink if specified."""
    # Activate the env
    venv_path = PoetryAPI.activate_env(python_version)

    # Create the link if needed
    if link:
        Settings.venv_link_path.unlink(missing_ok=True)
        Settings.venv_link_path.symlink_to(venv_path)


def env_init(
    c: Runner, python_version: str, link: bool = True, rebuild: bool = False
) -> None:
    """Create a poetry env, installing all project dependencies. If needed, it can rebuild said env."""

    # Delete an existing env if a rebuilt is needed
    if rebuild and PoetryAPI.is_env_available(python_version):
        env_remove(python_version, quiet=False, rm_link=False)

    info(f"Activating {python_version} env.")
    env_activate(python_version, link)

    # Install all dependencies
    info("Installing project dependencies.")

    # import here to avoid circular import
    from invoke_poetry.main import install_project_dependencies

    install_project_dependencies(c, quiet=False)


def env_remove(version: str, quiet: bool = False, rm_link: bool = True) -> None:
    """Remove the specified poetry virtualenv, deleting the relative symlink if required."""
    removed_path = PoetryAPI.remove_env(version)

    if (
        rm_link
        and Settings.venv_link_path.is_symlink()
        and Path(os.readlink(Settings.venv_link_path)) == removed_path
    ):
        # if Settings.venv_link_path is a link that points to the removed env, and it should be removed
        Settings.venv_link_path.unlink()
        if not quiet:
            info(f"'{Settings.venv_link_path}' link removed.")


def env_get_list() -> List[str]:
    """Prepare a colored list of poetry virtualenv."""
    active_env_version = PoetryAPI.get_active_project_env_version()
    versions = []

    for version in sorted(PoetryAPI.get_available_env_names(), key=natural_sort_key):
        env_str = f"\t{version}"
        if version == active_env_version:
            env_str = f"{Colors.OKBLUE}{env_str}\t(activated){Colors.ENDC}"
        versions.append(env_str)

    return versions


#
# ENV UTILS
#


def validate_env_version(python_version: Optional[str]) -> str:
    """TODO"""
    if not python_version:
        python_version = Settings().default_python_version
    # supported_python_version is a property, cache its return value
    supported_python_versions = Settings().supported_python_versions
    if python_version not in supported_python_versions:
        error(
            f"Unsupported python version: choose between {supported_python_versions}",
        )
    return python_version


@contextmanager
def active_env(
    python_version: str,
    quiet: bool = True,
    rollback_env: bool = True,
    link: bool = False,
) -> Generator[None, None, None]:
    """TODO"""
    previously_active_version = PoetryAPI.get_active_project_env_version()
    active_version = previously_active_version

    try:
        with delay_keyboard_interrupt():
            # activate the new virtual env, if needed
            if python_version != previously_active_version:
                env_activate(python_version, link=link)
                active_version = python_version
                if not quiet:
                    info(f"Activated env: {python_version}")
        yield
    finally:
        if rollback_env:
            env_rollback_if_needed(
                previously_active_version,
                active_version=active_version,
                quiet=quiet,
                link=link,
            )


def env_rollback_if_needed(
    previously_active_version: Optional[str],
    active_version: Optional[str] = None,
    quiet: bool = True,
    link: bool = False,
) -> None:
    """TODO"""
    if previously_active_version:
        # There actually was a previously active poetry env
        with delay_keyboard_interrupt():
            if not active_version:
                active_version = PoetryAPI.get_active_project_env_version()
            if previously_active_version != active_version:
                # rollback to the old env, if needed
                env_activate(previously_active_version, link=link)
                if not quiet:
                    info(f"Reactivated env: {previously_active_version}")


@contextmanager
def remember_active_env(quiet: bool = True) -> Generator[None, None, None]:
    """A context manager that makes sure to go back to the previously active poetry venv."""
    old_active_version = PoetryAPI.get_active_project_env_version()
    try:
        yield
    finally:
        env_rollback_if_needed(old_active_version, quiet=quiet, link=True)


#
# INVOKE ENV COLLECTION
#

env = PatchedInvokeCollection("env")


@env.task(
    name="use",
    default=True,
    help={
        "python_version": "target python version",
        "no_link": "avoid creating a link to .venv",
    },
)
def env_use_task(
    _: Runner,
    python_version: Optional[str] = None,
    no_link: bool = False,
) -> None:
    """Activate a poetry virtual environment. Optionally link it to .venv."""
    if not python_version:
        info("No python version specified, activating default env.")
    python_version = validate_env_version(python_version)
    env_activate(python_version, link=not no_link)
    ok(f"Env {python_version} activated.")


@env.task(name="list")
def env_list_task(_: Runner) -> None:
    """Show all associated venv and the active one."""
    info("Poetry virtual environments:")
    for version in env_get_list():
        print(version)


@env.task(
    name="remove",
    help={
        "python_version": "target associated venv",
        "all": "delete all associated venv instead of a specific version",
        "rm_link": "also delete the '.venv' link. Default: True",
    },
)
def env_remove_task(
    _: Runner,
    python_version: Optional[str] = None,
    rm_link: bool = True,
    all: bool = False,
) -> None:
    """Remove the specified python virtualenv.

    Either '-p / python-version [version]' or '-a / --all' flags need to be present."""
    if all:
        for version in Settings().supported_python_versions:
            if PoetryAPI.is_env_available(version):
                env_remove(version, quiet=False, rm_link=rm_link)
            else:
                warn(f"Could not find a {version} env to delete.")
        ok("Virtual envs deleted")
    elif python_version:
        if (
            python_version in Settings().supported_python_versions
            and PoetryAPI.is_env_available(python_version)
        ):
            env_remove(python_version, quiet=False, rm_link=rm_link)
            ok("Virtual env deleted")
        else:
            warn(f"Could not find a {python_version} env to delete.")
    else:
        error(
            "Either '-p / python-version [version]' or '-a / --all' flags need to be present."
        )


@env.task(
    name="init",
    help={
        "python_version": "target associated venv",
        "all": "init all supported venv instead of a specific version",
        "link": "link the venv to '~/.venv'. Default: True",
        "rebuild": "recreate existing venvs. Default: False",
    },
)
def env_init_task(
    c: Runner,
    python_version: Optional[str] = None,
    link: bool = True,
    all: bool = False,
    rebuild: bool = False,
) -> None:
    """Create a venv and install the project dependencies using a customizable hook.

    By default, the hook run 'poetry install' inside the venv."""
    with remember_active_env(quiet=False):
        if all:
            for version in reversed(list(Settings().supported_python_versions)):
                env_init(c, version, link, rebuild)
        else:
            python_version = validate_env_version(python_version)
            env_init(c, python_version, link, rebuild)
    ok("Done")
