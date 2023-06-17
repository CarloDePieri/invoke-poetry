#
# ABOUT THIS MODULE
#
# This addresses two problems Invoke currently has:
# - type hints are broken (PR#916 https://github.com/pyinvoke/invoke/pull/916);
# - the API for adding a task to a collection could be better (PR#527 https://github.com/pyinvoke/invoke/pull/527).
#
import sys
from typing import Any, Callable, Protocol, TypeVar, Union, cast, overload

from invoke import Collection, Task, task  # type: ignore[attr-defined]

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")
R = ParamSpec("R")


class CollectionDecorator:
    """An overloaded (it can be used both as `@task` and as `@task(...)`, collection specific decorator
    that will register the decorated function as that collection's task.

    It also tries to address invoke broken type hints: decorated functions, that at runtime will be `invoke.Task`
    instances, will be seen by type checkers and IDEs as Callable with correct arguments and return types.

    If the need arise to use the decorated function as `invoke.Task`, the `cast_to_task` function can be used.

    ```python
    ns = Collection()
    docs = Collection("docs")
    ns.add_collection(docs)
    doc_task = CollectionDecorator(docs).decorator

    @doc_task
    def docs(c: Runner, version: str) -> int:
        ...

    reveal_type(docs)  # (Runner, str) -> int
    ```
    """

    collection: Collection

    def __init__(self, collection: Collection):
        self.collection = collection

    @overload
    def decorator(self, __func: Callable[P, T]) -> Callable[P, T]:
        ...

    @overload
    def decorator(
        self, *args: Task[Callable[..., Any]], **kwargs: Any
    ) -> Callable[[Callable[R, T]], Callable[R, T]]:
        ...

    def decorator(
        self, *args: Union[Callable[P, T], Task[Callable[..., Any]]], **kwargs: Any
    ) -> Union[Callable[P, T], Callable[[Callable[R, T]], Callable[R, T]]]:
        """This method should be used directly to decorate target functions."""

        def inner(func: Callable[R, T]) -> Callable[R, T]:
            # Call the invoke.task decorator, casting the result to invoke.Task, as it should be (and is at runtime)
            new_task = cast(Task[Callable[..., Any]], task(func, **kwargs))
            # Add the new task to the saved collection
            self.collection.add_task(new_task)
            # Return the task cast as a Callable to keep re-usability
            return cast(Callable[R, T], new_task)

        if len(args) == 1 and not isinstance(args[0], Task):
            # @task
            return inner(args[0])
        else:
            # @task(...)
            if args:
                # handle pre-task
                if "pre" in kwargs:
                    raise TypeError(
                        "May not give *args and 'pre' kwarg simultaneously!"
                    )
                kwargs["pre"] = args
            return inner


class OverloadedDecoratorType(Protocol):
    """A protocol is needed to describe the overloaded decorator type in functions that return it."""

    @overload
    def __call__(self, __func: Callable[P, T]) -> Callable[P, T]:
        """Decorator type when being used as `@decorator`."""

    # Protocols do not use an actual implementation, only need the overloaded `__call__`, so:
    # noinspection PyOverloads
    @overload
    def __call__(
        self, *args: Task[Callable[..., Any]], **kwargs: Any
    ) -> Callable[[Callable[R, T]], Callable[R, T]]:
        """Decorator type when being used as `@decorator(...)`."""


def as_task(func: F) -> Task[F]:
    """Convenience used to cast a function decorated with `CollectionDecorator` back to a `invoke.Task`.

    This is useful to maintain type correctness in certain cases, like when specifying pre tasks directly:

    ```python
    @task
    def task_a():
        pass

    @task(as_task(a))  # task_a would be a Callable when using a CollectionDecorator, not a Task, hence the needed cast
    def task_b():
        pass
    """
    return cast(Task[F], func)
