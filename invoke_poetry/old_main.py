import signal
import sys
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import tomli
from invoke import Runner, Task, task

#
# MISC
#


def check_python_version(python_version: str):
    supported_python_versions = Settings().supported_python_versions
    if python_version not in supported_python_versions:
        error(
            f"Unsupported python version: choose between {supported_python_versions}",
        )


def get_active_local_poetry_env_version() -> Optional[str]:
    """Return the version of the active, local poetry environment's python version"""
    env_file = Path(".venvs") / "envs.toml"
    if env_file.is_file():
        with open(".venvs/envs.toml", "rb") as f:
            toml_dict = tomli.load(f)
            env_data = list(toml_dict.values())[0]
            return env_data["minor"]
    else:
        return None


def pr(cmd, c, verbose_level: Verbose = Verbose.TWO, **kwargs) -> None:
    """Use inside a poetry_env block to execute command inside the env via 'poetry run'.

    ```python
    @task
    def get_version(c):
        with poetry_venv(c, '3.7'):
            pr("python --version", c)
    ```
    """
    patched_cmd = f"poetry run {cmd}"
    if verbose_level == Verbose.TWO:
        info(patched_cmd)
    if "hide" not in kwargs:
        kwargs["hide"] = verbose_level == Verbose.ZERO
    c.run(patched_cmd, **kwargs)


def get_additional_args() -> List[str]:
    if "--" not in sys.argv:
        return []
    else:
        delimiter = sys.argv.index("--") + 1
        return sys.argv[delimiter:]


def get_additional_args_string() -> str:
    def wrap_in_quote(x: str) -> str:
        # Try to handle quoted arguments
        if " " in x:
            return f'"{x}"'
        else:
            return x

    args = list(map(wrap_in_quote, get_additional_args()))
    if args:
        return " " + " ".join(args)
    else:
        return ""


def _install_project_dependencies_default_hook(
    c: Runner, verbose_level: Verbose = Verbose.TWO
) -> None:
    if verbose_level == Verbose.TWO:
        info("poetry install")
    c.run("poetry install", hide=verbose_level == Verbose.ZERO, pty=True)


def install_project_dependencies(
    c: Runner, verbose_level: Verbose = Verbose.TWO
) -> None:
    Settings.install_project_dependencies_hook(c, verbose_level)


class Settings:

    install_project_dependencies_hook = _install_project_dependencies_default_hook
    _dev_python_version: Optional[str] = None
    _supported_python_versions: Optional[List[str]] = None
    _configured = False

    @staticmethod
    def init(
        ns: Collection,
        dev_python_version: str,
        supported_python_versions: List[str],
        install_project_dependencies_hook: Optional[Callable] = None,
    ):
        Settings._configured = True
        ns.add_collection(env)
        Settings._dev_python_version = dev_python_version
        Settings._supported_python_versions = supported_python_versions
        if install_project_dependencies_hook:
            Settings.install_project_dependencies_hook = (
                install_project_dependencies_hook
            )

    @property
    def dev_python_version(self) -> str:
        if not self._configured:
            self.exit_with_configuration_error()
        return self._dev_python_version

    @property
    def supported_python_versions(self) -> List[str]:
        if not self._configured:
            self.exit_with_configuration_error()
        return self._supported_python_versions

    @staticmethod
    def exit_with_configuration_error():
        error("CONFIGURATION ERROR", exit_now=False)
        print(
            "\n\tRead the module documentation!\n\n"
            "\tYou need a call to Settings.init( ... ) in your tasks file.\n"
        )
        error("CONFIGURATION ERROR")


#
# ENV MANAGEMENT
#

# Global variable used to handle ctrl+c
keyboard_interrupted = False


def env_use(
    c: Runner,
    python_version: Optional[str] = None,
    link: bool = True,
    verbose_level: Verbose = Verbose.TWO,
) -> None:
    """Activate a poetry virtual environment. Optionally link it to .venv."""

    if not python_version:
        python_version = Settings().dev_python_version

    quiet_str = " -q" if verbose_level == Verbose.ZERO else ""
    c.run(f"poetry env use python{python_version}{quiet_str}", pty=True)

    if link:
        venv_path = c.run("poetry env info -p", hide=True).stdout.rstrip("\n")
        c.run(f"rm -f .venv && ln -sf {venv_path} .venv")

    ok(f"Env {python_version}{'' } activated", verbose=verbose_level == Verbose.TWO)


@contextmanager
def poetry_venv(
    c: Runner, python_version: str = None, verbose_level: Verbose = Verbose.ZERO
):
    """Context manager that will execute all commands inside with the selected poetry
    virtualenv.
    It will restore the previous virtualenv (if one was active) after it's done.

    ```python
    @task
    def get_version(c):
        with poetry_venv(c, '3.7'):
            c.run("poetry run python --version")
    ```

    """
    if not python_version:
        python_version = Settings().dev_python_version
    # TODO handle cache
    # Find out if a local poetry env was active
    old_env_python_version = get_active_local_poetry_env_version()
    old_env_exists = old_env_python_version is not None

    if old_env_exists:

        if python_version != old_env_python_version:
            # A new env needs to be activated
            should_activate_new_env = True
            should_link_new_env = False
            should_restore_old_env = True

        else:
            # The already active environment is the right one, do nothing
            should_activate_new_env = False
            should_link_new_env = False
            should_restore_old_env = False

    else:
        # poetry did not have an environment active
        old_env_python_version = None
        should_activate_new_env = True
        should_link_new_env = True
        should_restore_old_env = False

    if should_activate_new_env:
        env_use(
            c,
            python_version,
            link=should_link_new_env,
            verbose_level=verbose_level,
        )

    try:
        # inject the python version in the Runner object
        c.poetry_python_version = python_version
        # execute the wrapped code block
        yield
    finally:
        if should_restore_old_env:
            env_use(
                c,
                old_env_python_version,
                link=True,
                verbose_level=verbose_level,
            )


def task_in_poetry_env_matrix(python_versions: List[str]):
    """A decorator that allows to repeat an invoke task in the specified poetry venvs.
    Must be called between the @task decorator and the decorated function, like this:

    ```python
    @task
    @task_in_poetry_env_matrix(python_versions=['3.7', '3.8'])
    def get_version(c):
        c.run("poetry run python --version")
    ```

    """

    def wrapper(decorated_function):
        def task_wrapper(c, *args, **kwargs):

            # Make sure ctrl+c is handled correctly
            signal.signal(signal.SIGINT, _ctrl_c_handler)

            # Check all proposed python version are valid
            for version in python_versions:
                check_python_version(version)

            info("Job matrix started")
            results = {}

            # Define a job (it's the decorated function!)
            def job():
                decorated_function(c, *args, **kwargs)

            # For every python version, execute the job
            for version in python_versions:
                results[version] = _execute_job(c, version, job)

            # Print a final report
            _print_job_matrix_report(results, python_versions)

        return task_wrapper

    return wrapper


def _execute_job(c: Runner, version: str, job: Callable) -> str:
    """Execute the defined job in the selected poetry env, returning the result
    as a string."""
    global keyboard_interrupted

    if not keyboard_interrupted:
        try:
            with poetry_venv(c, version):
                info(f"Venv {version}: enabled")
                job()
            ok(f"Venv {version}: success")
            return "success"

        except (Exception,):
            if keyboard_interrupted:
                error(f"Venv {version}: INTERRUPTED", exit_now=False)
                return "interrupted"
            else:
                error(f"Venv {version}: FAILED", exit_now=False)
                return "failure"
    else:
        return "skipped"


def _ctrl_c_handler(_, __) -> None:
    """When ctrl-c is captured, set the 'keyboard_interrupted' global variable."""
    global keyboard_interrupted
    keyboard_interrupted = True
    raise KeyboardInterrupt


def _print_job_matrix_report(
    results: Dict[str, str], python_versions: List[str]
) -> None:
    """Print a report at the end of a matrix job run."""
    # Print the matrix result
    info("Job matrix result:")
    for venv in python_versions:
        state = results[venv]
        color = {
            "success": Colors.OKGREEN,
            "interrupted": Colors.FAIL,
            "failure": Colors.FAIL,
            "skipped": Colors.OKBLUE,
        }[state]
        print(f"\t{color} - python{venv}: {state}{Colors.ENDC}")
    # Print a final result message
    results_values = results.values()
    if "failure" in results_values:
        error("Failed")
    elif "interrupted" in results_values:
        error("Interrupted")
    elif "skipped" in results_values:
        warn("Done (but some job skipped!)")
    else:
        ok("Done")


#
# ENV TASKS
#
env = Collection("env")


@env.task(name="use", default=True)
def env_use_task(c, python_version=None):

    if not python_version:
        python_version = Settings().dev_python_version

    check_python_version(python_version)
    env_use(c, python_version)


@env.task(name="list")
def env_list(c):
    cmd = "poetry env list"
    info(cmd)
    c.run(cmd, pty=True)


@env.task(name="clean")
def env_clean(c):
    cmd = "rm -rf .venvs && rm -f .venv"
    info(cmd)
    c.run(cmd)
    ok("Virtual envs deleted")


@env.task(name="rebuild")
def env_rebuild(c):

    s = Settings()
    supported_python_versions = s.supported_python_versions
    dev_python_version = s.dev_python_version

    env_clean(c)
    for venv in supported_python_versions:
        if venv != dev_python_version:
            env_use(c, venv, link=False, verbose_level=Verbose.ONE)
            install_project_dependencies(c)
    env_use(c, dev_python_version, link=True, verbose_level=Verbose.ONE)
    install_project_dependencies(c)
    ok("Virtual envs rebuilt")
