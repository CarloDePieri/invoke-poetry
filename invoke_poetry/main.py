from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from invoke import Runner
from invoke.exceptions import UnexpectedExit

from invoke_poetry.collection import PatchedInvokeCollection
from invoke_poetry.env import (
    env,
    env_activate,
    get_active_env_version,
    remember_active_env,
    validate_env_version,
)
from invoke_poetry.logs import error, info, warn
from invoke_poetry.settings import Settings
from invoke_poetry.utils import IsInterrupted, capture_signal


def init_ns(
    default_python_version: Optional[str] = None,
    supported_python_versions: Optional[Iterable[str]] = None,
    install_project_dependencies_hook: Optional[Callable[..., Any]] = None,
) -> Tuple[PatchedInvokeCollection, Callable]:
    """Prepare the root invoke collection and set all required settings.
    Invoke REQUIRES a root collection specifically named 'ns' in the tasks.py file, so use this function like this:

    ```python
    from invoke_poetry import init_ns

    # make sure the collection returned by init_ns is named 'ns'
    ns, task = init_ns()

    @task
    def my_task(c):
        c.run("echo 'hello world!'")
    ```
    """

    ns = PatchedInvokeCollection()

    # Save specified settings in the Settings namespace
    Settings().init(
        default_python_version,
        supported_python_versions,
        install_project_dependencies_hook=install_project_dependencies_hook,
    )

    # inject the env collection
    # ns.add_collection(env)

    return ns, ns.task


def add_sub_collection(
    collection: PatchedInvokeCollection, name: str
) -> Tuple[PatchedInvokeCollection, Callable]:
    """Convenience function to create a new sub collection in a collection and get access to the new `.task` decorator."""
    sub = PatchedInvokeCollection(name)
    collection.add_collection(sub)
    return sub, sub.task


@contextmanager
def poetry_venv(c: Runner, python_version: Optional[str] = None) -> None:
    """Context manager that will execute all Runner.run() commands inside the selected
    poetry virtualenv.
    It will restore the previous virtualenv (if one was active) after it's done.

    ```python
    @task
    def get_version(c, python_version="3.7"):

        with poetry_venv(c, python_version):
            c.run("python --version")  # will run as 'poetry run python --version'

        c.run("python --version")  # will run normally as 'python --version'
    ```
    """
    capture_signal()

    try:
        # validate the given python version
        python_version = validate_env_version(python_version)

        # remember the active virtual env and come back to it when all is done
        with remember_active_env(c, quiet=False):

            # activate the new virtual env, if needed
            if python_version != get_active_env_version(c):
                env_activate(c, python_version, link=False)
                info(f"Activated env: {python_version}")

            # patch the run method inside this context manager
            c.run_outside = c.run

            def poetry_run(*args, **kwargs) -> None:
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
                if IsInterrupted.by_user:
                    # User sent a ctrl-c
                    warn("Poetry task manually interrupted")
                # restore the original run method
                c.run = c.run_outside
                delattr(c, "run_outside")
    except (KeyboardInterrupt, UnexpectedExit) as e:

        if IsInterrupted.by_user:
            if not TaskMatrix.running:
                # If the user interrupted a single job, exit now with an error message
                error("User aborted!", exit_now=True)
            else:
                # Raise the error so that it can be caught by the matrix logic
                raise e
        else:
            # This was not a user interrupt, so it should simply raise the error
            raise e


def install_project_dependencies(c: Runner, *args, **kwargs) -> Any:
    """A convenience function to call the install_project_dependencies hook (either the custom or the default one).
    It will pass forward every argument."""
    return Settings.install_project_dependencies_hook(c, *args, **kwargs)


class TaskMatrix:

    jobs: Dict[str, str] = {}
    running = False

    @staticmethod
    def print_report():
        print(TaskMatrix.jobs)

    @staticmethod
    def reset():
        TaskMatrix.running = False
        TaskMatrix.jobs = {}


def task_matrix(
    hook: Callable,
    hook_args_builder: Callable[[str], Tuple[List, Dict]],
    task_names: List[str],
) -> None:
    """TODO"""

    capture_signal()
    TaskMatrix.running = True

    for name in task_names:
        try:
            if IsInterrupted.by_user:
                warn(f"task {name}: SKIPPED")
                TaskMatrix.jobs[name] = "skipped"
            else:
                info(f"task {name}: RUNNING")
                hook_args, hook_kwargs = hook_args_builder(name)
                hook(*hook_args, **hook_kwargs)
                TaskMatrix.jobs[name] = "success"
                info(f"task {name}: SUCCESS")
        except (BaseException,) as e:
            if not IsInterrupted.by_user:
                print(e)
                error(f"task {name}: FAILED", exit_now=False)
                TaskMatrix.jobs[name] = "failed"
            else:
                warn(f"task {name}: INTERRUPTED")
                TaskMatrix.jobs[name] = "interrupted"
                IsInterrupted.by_user = True

    TaskMatrix.print_report()
    TaskMatrix.reset()
