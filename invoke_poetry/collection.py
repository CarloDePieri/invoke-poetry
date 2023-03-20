from __future__ import annotations

from typing import Any, Callable, Union

from invoke import Collection as InvokeCollection
from invoke import Task, task


class PatchedInvokeCollection(InvokeCollection):  # type: ignore[misc]
    """Custom invoke Collection that allows for a saner API.
    Waiting for invoke PR#789 https://github.com/pyinvoke/invoke/pull/789"""

    def task(self, *args: Any, **kwargs: Any) -> Union[Task, Callable[..., Task]]:
        """
        Wrap a callable object and register it to the current collection.
        """
        maybe_task: Union[Task, Callable[..., Any]] = task(*args, **kwargs)

        if isinstance(maybe_task, Task):
            self.add_task(maybe_task)
            return maybe_task

        def inner(*b_args: Any, **b_kwargs: Any) -> Task:
            configured_task = maybe_task(*b_args, **b_kwargs)
            self.add_task(configured_task)
            return configured_task

        return inner
