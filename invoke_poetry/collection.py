import inspect
from typing import Any, Callable, Union
from unittest.mock import patch

from invoke import Collection as InvokeCollection
from invoke import Task, task


class PatchedInvokeCollection(InvokeCollection):  # type: ignore[misc]
    """Patched invoke Collection to suit my workflow.

    - Allows to define tasks in (sub)collections; waiting for https://github.com/pyinvoke/invoke/pull/789
    - Allows to use type annotation on tasks, using a patched Task class; waiting for https://github.com/pyinvoke/invoke/pull/606
    """

    def task(self, *args: Any, **kwargs: Any) -> Union[Task, Callable[..., Task]]:
        """
        Wrap a callable object and register it to the current collection.
        """

        maybe_task: Union[Task, Callable[..., Any]] = task(
            *args, klass=PatchedTask, **kwargs
        )

        if isinstance(maybe_task, Task):
            self.add_task(maybe_task)
            return maybe_task

        def inner(*b_args: Any, **b_kwargs: Any) -> Task:
            configured_task = maybe_task(*b_args, **b_kwargs)
            self.add_task(configured_task)
            return configured_task

        return inner


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
