import signal
import subprocess
from contextlib import contextmanager
from pathlib import Path
from subprocess import check_output
from typing import Any, Generator, Optional

delayed_interrupt = False


class IsInterrupted:
    by_user = False
    delayed = False


@contextmanager
def delay_keyboard_interrupt() -> Generator[None, None, None]:
    """TODO"""

    def _interrupt(_: Any, __: Any) -> None:
        IsInterrupted.delayed = True

    original = signal.signal(signal.SIGINT, _interrupt)
    yield
    signal.signal(signal.SIGINT, original)
    if IsInterrupted.delayed:
        raise KeyboardInterrupt


def ctrl_c_handler(_: Any, __: Any) -> None:
    """When ctrl-c is captured, TODO."""
    # do stuff - this is needed when ctrl-c is pressed when a c.run is executing
    IsInterrupted.by_user = True
    raise KeyboardInterrupt


def capture_signal() -> None:
    signal.signal(signal.SIGINT, ctrl_c_handler)


def look_for_poetry_env_file() -> Optional[Path]:

    # get the virtualenvs.path config value and build a Path from there
    try:
        env_folder = Path(
            check_output("poetry config virtualenvs.path".split(" "))
            .decode("UTF-8")
            .rstrip("\n")
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    if env_folder.is_absolute():
        env_file = env_folder / "envs.toml"
    else:
        # look for a possible project root, otherwise use cwd
        project_root = search_upwards_for_project_root()
        if project_root:
            root = project_root
        else:
            root = Path(".").absolute()
        env_file = root / env_folder / "envs.toml"

    if env_file and env_file.exists():
        return env_file
    return None


def search_upwards_for_project_root(
    file_in_root: str = "pyproject.toml",
) -> Optional[Path]:
    file = find_file_upwards(Path(".").absolute(), file_in_root)
    return file.parent if file else None


def find_file_upwards(cwd: Path, filename: str) -> Optional[Path]:
    if cwd == Path(cwd.root) or cwd == cwd.parent:
        return None
    fullpath = cwd / filename
    return fullpath if fullpath.exists() else find_file_upwards(cwd.parent, filename)
