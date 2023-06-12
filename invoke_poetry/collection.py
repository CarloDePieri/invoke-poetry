from typing import Any, Callable, TypeVar, Union, cast

from invoke import Collection as InvokeCollection  # type: ignore[attr-defined]
from invoke import Task, task  # type: ignore[attr-defined]

InvokeTask = TypeVar("InvokeTask", bound=Task)
F = TypeVar("F", bound=Callable[..., Any])


class PatchedInvokeCollection(InvokeCollection):
    """Patched invoke Collection to suit my workflow.

    Allows to define tasks in (sub)collections; waiting for https://github.com/pyinvoke/invoke/pull/789 or
    https://github.com/pyinvoke/invoke/pull/527 .
    """

    def task(
        self, *args: Any, **kwargs: Any
    ) -> Union[InvokeTask, Callable[[F], InvokeTask]]:
        """Register a task.

        By supporting python 3.8, this is the better we can annotate this decorator. Mypy will not complain most of the
        time, but it may need some convincing in certain specific cases (see 'nothing cannot be called'):

        @task(name="dev")
        def dev(c: Runner) -> int:
            return 42

        dev(c)  # broken for mypy
        cast(Callable[[Runner], int], dev)(c)  # working
        """

        def _added_task(_task: Task) -> InvokeTask:
            """Register the task and returns a cast object, useful for mypy."""
            self.add_task(_task)
            return cast(InvokeTask, _task)

        maybe_task = task(*args, klass=Task, **kwargs)

        if isinstance(maybe_task, Task):
            # called by @task , return the Task callable object
            return _added_task(maybe_task)

        else:
            # called by @task() , return the function that will return the Task callable object
            def wrapper(func: F) -> InvokeTask:
                return _added_task(maybe_task(func))

            return wrapper
