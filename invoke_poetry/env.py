import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from invoke import Result, Runner

from invoke_poetry.collection import PatchedInvokeCollection
from invoke_poetry.logs import error, info, ok, warn
from invoke_poetry.settings import Settings
from invoke_poetry.utils import delay_keyboard_interrupt

#
# ENV OPERATIONS
#


def env_activate(
    c: Runner,
    python_version: str,
    link: bool = True,
) -> None:
    """TODO"""
    # Activate the env
    c.run(f"poetry env use {python_version} -q", pty=True)

    # Create the link if needed
    if link:
        venv_path = get_active_env_path(c)
        if venv_path:
            c.run(f"rm -f .venv && ln -sf {venv_path} .venv")


def env_init(
    c: Runner, python_version: str, link: bool = True, rebuild: bool = False
) -> None:
    """TODO"""

    # Delete an existing env if a rebuilt is needed
    if rebuild and env_exists(c, python_version):
        env_remove(c, python_version, quiet=False, rm_link=False)

    info(f"Activating {python_version} env.")
    env_activate(c, python_version, link)

    # Install all dependencies
    info("Installing project dependencies.")

    # import here to avoid circular import
    from invoke_poetry.main import install_project_dependencies

    install_project_dependencies(c, quiet=False)


def env_remove(
    c: Runner, version: str, quiet: bool = False, rm_link: bool = True
) -> None:
    """TODO"""
    cmd = f"poetry env remove python{version}"
    if not quiet:
        info(cmd)

    result = c.run(cmd, hide=True)

    if rm_link and os.path.islink(".venv"):
        # if .venv is a link and should be removed...
        venv_link = Path(os.readlink(".venv"))
        deleted_virtualenv_path = Path(
            result.stdout.replace("Deleted virtualenv: ", "").replace("\n", "")
        )
        if deleted_virtualenv_path == venv_link:
            # ... and it points to the removed venv
            cmd = "rm -f .venv"
            if not quiet:
                info(cmd)
            c.run(cmd)


#
# ENV UTILS
#


def env_exists(c: Runner, version: str) -> bool:
    """TODO"""
    cmd = f"poetry env list | grep {version}"
    out: Result = c.run(cmd, hide=True, warn=True)
    env_found: bool = out.ok
    return env_found


def get_active_env_path(c: Runner) -> Optional[str]:
    """TODO"""
    result: Result = c.run("poetry env info -p", hide=True, warn=True)
    stdout: str = result.stdout
    if result.ok:
        return stdout.rstrip("\n")
    else:
        return None


def get_active_env_version(c: Runner) -> Optional[str]:
    """TODO"""
    path = get_active_env_path(c)
    if path:
        regex = r"py(\d\.\d*)"
        matches = re.finditer(regex, path, re.MULTILINE)
        for match in matches:
            for group in match.groups():
                return group
    return None


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
def remember_active_env(
    c: Runner, quiet: bool = True, skip_rollback: bool = False
) -> Generator[None, None, None]:
    """A context manager that makes sure to go back to the previously active poetry venv. The rollback can be skipped
    dynamically."""
    if skip_rollback:
        yield
    else:
        old_active_version = get_active_env_version(c)
        try:
            yield
        finally:
            with delay_keyboard_interrupt():
                active_version = get_active_env_version(c)
                if old_active_version and active_version != old_active_version:
                    env_activate(c, old_active_version)
                    if not quiet:
                        info(f"Reactivated env: {old_active_version}")


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
    c: Runner,
    python_version: Optional[str] = None,
    no_link: bool = False,
) -> None:
    """Activate a poetry virtual environment. Optionally link it to .venv."""
    if not python_version:
        info("No python version specified, activating default env.")
    python_version = validate_env_version(python_version)
    env_activate(c, python_version, link=not no_link)
    ok(f"Env {python_version} activated.")


@env.task(name="list")
def env_list_task(c: Runner) -> None:
    """Show all associated venv and the active one."""
    info("Poetry virtual environments:")
    c.run("poetry env list", pty=True)


@env.task(
    name="remove",
    help={
        "python_version": "target associated venv",
        "all": "delete all associated venv instead of a specific version",
        "rm_link": "also delete the '.venv' link. Default: True",
    },
)
def env_remove_task(
    c: Runner,
    python_version: Optional[str] = None,
    rm_link: bool = True,
    all: bool = False,
) -> None:
    """Remove the specified python virtualenv.

    Either '-p / python-version [version]' or '-a / --all' flags need to be present."""
    if all:
        for version in Settings().supported_python_versions:
            if env_exists(c, version):
                env_remove(c, version, quiet=False, rm_link=rm_link)
            else:
                warn(f"Could not find a {version} env to delete.")
        ok("Virtual envs deleted")
    elif python_version:
        if python_version in Settings().supported_python_versions and env_exists(
            c, python_version
        ):
            env_remove(c, python_version, quiet=False, rm_link=rm_link)
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
    with remember_active_env(c, quiet=False):
        if all:
            for version in reversed(list(Settings().supported_python_versions)):
                env_init(c, version, link, rebuild)
        else:
            python_version = validate_env_version(python_version)
            env_init(c, python_version, link, rebuild)
    ok("Done")
