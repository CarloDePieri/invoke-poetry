from __future__ import annotations

import enum
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Generator, Iterable, List, Tuple

from invoke_poetry.logs import Colors, error, info, warn
from invoke_poetry.utils import IsInterrupted, capture_signal


class TaskState(enum.Enum):
    """Represent a matrix task state."""

    RUNNING = -1
    OK = 0
    FAILED = 1
    SKIPPED = 2
    INTERRUPTED = 3

    def get_colored_name(self) -> str:
        """Return a colored state name."""
        return f"{self.get_color()}{Colors.BOLD}{self.name}{Colors.ENDC}"

    def get_color(self) -> str:
        """Match a color with a specific state"""
        return [
            Colors.HEADER,  # running
            Colors.OKGREEN,  # ok
            Colors.FAIL,  # failed
            Colors.BLUE,  # skipped
            Colors.WARNING,  # interrupted
        ][self.value + 1]


@dataclass
class MatrixTask:
    """A matrix task, with a `name` and its current `state`.

    When concluded, if the task returned something, it may be found in the `returned` field.
    """

    name: str
    state: TaskState = TaskState.RUNNING
    returned: Any = None

    def report_state(self) -> None:
        """Print a report that illustrates the task state."""
        reporter, kwargs = self._get_reporter()
        reporter(f"task {self.name}: {self.state.name}", **kwargs)  # type: ignore[call-arg]

    def _get_reporter(self) -> Tuple[Callable[[str, bool], None], Dict[str, Any]]:
        """Return a reporter function and its kwargs based on the task state."""
        return [
            (info, {"do_print": True}),  # running
            (info, {"do_print": True}),  # ok
            (error, {"exit_now": False}),  # failed
            (warn, {"do_print": True}),  # skipped
            (warn, {"do_print": True}),  # interrupted
        ][self.state.value + 1]


@dataclass
class TaskMatrix:
    """A task matrix."""

    # The tasks list
    tasks: List[MatrixTask] = field(default_factory=lambda: [])
    # Whether to print all tasks steps
    quiet: bool = False

    # A class variable that indicates if a task matrix job is underway
    running: ClassVar[bool] = False

    def print_report(self) -> None:
        """Print a report of the current tasks states."""
        info("Test matrix results:\n")
        for task in self.tasks:
            print(f"\t{task.name}:\t{task.state.get_colored_name()}")

    def exit_with_rc(self) -> None:
        """Exit, possibly with an error if one of the task failed somehow."""
        for task in self.tasks:
            if task.state.value > 0:
                exit(1)
        exit()

    @staticmethod
    @contextmanager
    def new(quiet: bool = False) -> Generator[TaskMatrix, None, None]:
        """Context manager used to run a matrix job. It makes sure that the `running` class variable is correctly set."""
        TaskMatrix.running = True
        try:
            yield TaskMatrix(quiet=quiet)
        finally:
            TaskMatrix.running = False

    def register_new_task(
        self, name: str, state: TaskState, returned: Any = None
    ) -> None:
        """Create a new task starting from the given arguments and register it."""
        self.register_task(MatrixTask(name=name, state=state, returned=returned))

    def register_task(self, task: MatrixTask) -> None:
        """Register the given task."""
        if not self.quiet:
            task.report_state()
        self.tasks.append(task)


def task_matrix(
    hook: Callable[..., Any],
    hook_args_builder: Callable[[str], Tuple[List[Any], Dict[str, Any]]],
    task_names: Iterable[str],
    print_steps: bool = True,
) -> TaskMatrix:
    """TODO"""

    capture_signal()

    with TaskMatrix.new(quiet=not print_steps) as tm:

        for name in task_names:
            try:
                if IsInterrupted.by_user:
                    tm.register_new_task(name=name, state=TaskState.SKIPPED)
                else:
                    task = MatrixTask(name=name)
                    if print_steps:
                        task.report_state()
                    hook_args, hook_kwargs = hook_args_builder(name)
                    task.returned = hook(*hook_args, **hook_kwargs)
                    task.state = TaskState.OK
                    tm.register_task(task)
            except (BaseException,) as e:
                if not IsInterrupted.by_user:
                    print(e)
                    tm.register_new_task(name=name, state=TaskState.FAILED)
                else:
                    tm.register_new_task(name=name, state=TaskState.INTERRUPTED)
                    IsInterrupted.by_user = True

        return tm
