import inspect
from typing import Any, Callable, TypeVar, Union, cast
from unittest.mock import patch

from invoke import Collection as InvokeCollection
from invoke import Task, task

InvokeTask = TypeVar("InvokeTask", bound=Task)
F = TypeVar("F", bound=Callable[..., Any])


class PatchedInvokeCollection(InvokeCollection):  # type: ignore[misc]
    """Patched invoke Collection to suit my workflow.

    - Allows to define tasks in (sub)collections; waiting for https://github.com/pyinvoke/invoke/pull/789
    - Allows to use type annotation on tasks, using a patched Task class; waiting for https://github.com/pyinvoke/invoke/pull/606
    """

    def task(
        self, *args: Any, **kwargs: Any
    ) -> Union[InvokeTask, Callable[[F], InvokeTask]]:
        """
        TODO

        And document or fix the 'nothing can't be called'

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

        maybe_task = task(*args, klass=PatchedTask, **kwargs)

        if isinstance(maybe_task, Task):
            # called by @task , return the Task callable object
            return _added_task(maybe_task)

        else:
            # called by @task() , return the function that will return the Task callable object
            def wrapper(func: F) -> InvokeTask:
                return _added_task(maybe_task(func))

            return wrapper


class PatchedTask(Task):  # type: ignore[misc]
    """Replace all calls to the deprecated `getargspec` with `getfullargspec`."""

    def argspec(self, *args: Any, **kwargs: Any) -> Any:
        with patch("inspect.getargspec", wraps=self._patch):
            return super().argspec(*args, **kwargs)

    @staticmethod
    def _patch(func: Callable[..., Any]) -> Union[inspect.ArgSpec, inspect.FullArgSpec]:
        # noinspection PyDeprecation
        get_argspec = getattr(inspect, "getfullargspec", inspect.getargspec)
        return get_argspec(func)
