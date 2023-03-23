from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Optional, Tuple, Union

from invoke import Runner
from invoke.exceptions import UnexpectedExit

from invoke_poetry.collection import F, InvokeTask, PatchedInvokeCollection
from invoke_poetry.env import (
    active_env,
    env,
    env_activate,
    get_active_env_version,
    remember_active_env,
    validate_env_version,
)
from invoke_poetry.logs import error, info, warn
from invoke_poetry.matrix import TaskMatrix
from invoke_poetry.poetry_api import PoetryAPI
from invoke_poetry.settings import Settings
from invoke_poetry.utils import IsInterrupted, capture_signal


def init_ns(
    default_python_version: str,
    supported_python_versions: Optional[Iterable[str]] = None,
    install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
    poetry_env_file: Optional[str] = None,
) -> Tuple[PatchedInvokeCollection, Callable[..., Any]]:
    """Prepare the root invoke collection and set all required settings.
    Invoke REQUIRES a root collection specifically named 'ns' in the tasks.py file, so use this function like this:

    ```python
    from invoke_poetry import init_ns

    # make sure the collection returned by init_ns is named 'ns'
    ns, task = init_ns(default_python_version='3.7')

    @task
    def my_task(c):
        c.run("echo 'hello world!'")
    ```
    """
    ns = PatchedInvokeCollection()

    # Construct a default supported python versions
    if not supported_python_versions:
        supported_python_versions = [default_python_version]

    # Prepare the poetry config file path
    if poetry_env_file:
        poetry_env_file = Path(poetry_env_file)

    # Save specified settings in the Settings namespace
    Settings().init(
        default_python_version,
        supported_python_versions,
        install_project_dependencies_hook=install_project_dependencies_hook,
        poetry_env_file=poetry_env_file,
    )

    # Setup the poetry api
    PoetryAPI.init()

    # inject the env collection
    ns.add_collection(env)

    return ns, ns.task


def add_sub_collection(
    collection: PatchedInvokeCollection, name: str
) -> Tuple[
    PatchedInvokeCollection, Callable[..., Union[InvokeTask, Callable[[F], InvokeTask]]]
]:
    """Convenience function to create a new sub collection in a collection and get access to the new `.task` decorator."""
    sub = PatchedInvokeCollection(name)
    collection.add_collection(sub)
    return sub, sub.task


@contextmanager
def poetry_venv(
    c: Runner, python_version: Optional[str] = None, rollback_env: bool = True
) -> Generator[None, None, None]:
    """Context manager that will execute all Runner.run() commands inside the selected
    poetry virtualenv.
    It will restore the previous virtualenv (if one was active) after it's done, by default.

    ```python
    @task
    def get_version(c, python_version="3.7"):

        with poetry_venv(c, python_version):
            c.run("python --version")  # will run as 'poetry run python --version'

        c.run("python --version")  # will run normally as 'python --version'
    ```
    """
    with user_can_interrupt():
        # validate the given python version
        python_version = validate_env_version(python_version)

        # restore the previous env if needed after the context code block
        with active_env(
            c, python_version=python_version, quiet=False, rollback_env=rollback_env
        ):
            # patch the runner to prepend 'poetry run' to commands
            with patched_runner(c):
                # Execute the context manager code block
                yield


@contextmanager
def user_can_interrupt() -> Generator[None, None, None]:
    capture_signal()
    try:
        yield
    except (KeyboardInterrupt, UnexpectedExit) as e:
        if IsInterrupted.by_user:
            if not TaskMatrix.running:
                # If the user interrupted a single job, exit now with an error message
                error("User aborted!", exit_now=True)
            else:
                # Raise the error so that it can be caught by the matrix logic
                warn("Poetry task manually interrupted")
                raise e
        else:
            # This was not a user interrupt, so it should simply raise the error
            raise e


@contextmanager
def patched_runner(c: Runner) -> Generator[None, None, None]:
    # patch the run method inside this context manager
    c.run_outside = c.run

    def poetry_run(*args: Any, **kwargs: Any) -> None:
        if "command" in kwargs:
            cmd = kwargs["command"]
            command = f"poetry run {cmd}"
            del kwargs["command"]
        else:
            command = f"poetry run {args[0]}"
        return c.run_outside(command=command, **kwargs)

    c.run = poetry_run
    try:
        yield
    finally:
        # restore the original run method
        c.run = c.run_outside
        delattr(c, "run_outside")


def install_project_dependencies(c: Runner, *args: Any, **kwargs: Any) -> Any:
    """A convenience function to call the install_project_dependencies hook (either the custom or the default one).
    It will pass forward every argument."""
    return Settings.install_project_dependencies_hook(c, *args, **kwargs)
