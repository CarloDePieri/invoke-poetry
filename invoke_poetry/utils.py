import re
import signal
from contextlib import contextmanager
from typing import Any, Callable, Generator, List, Pattern, Union

delayed_interrupt = False


class IsInterrupted:
    by_user = False
    delayed = False


@contextmanager
def delay_keyboard_interrupt() -> Generator[None, None, None]:
    """Mimics a critical section: capture user SIGINTs arrived during the execution of the code block, delaying the
    interrupt effect to after the code block execution is done."""

    def _interrupt(_: Any, __: Any) -> None:
        IsInterrupted.delayed = True

    original = signal.signal(signal.SIGINT, _interrupt)
    yield
    signal.signal(signal.SIGINT, original)
    if IsInterrupted.delayed:
        raise KeyboardInterrupt


def flag_user_interrupt(_: Any, __: Any) -> None:
    """Used as signal handler, flag a user interrupt in the `IsInterrupted` class, then raise the
    `KeyboardInterrupt`."""
    IsInterrupted.by_user = True
    raise KeyboardInterrupt


def capture_sigint(handler: Callable[[Any, Any], None] = flag_user_interrupt) -> None:
    """Capture a sigint and execute the given handler. By default, call `flag_user_interrupt`."""
    signal.signal(signal.SIGINT, handler)


def natural_sort_key(
    string: str, _nsre: Pattern[str] = re.compile(r"(\d+)")
) -> List[Union[str, int, Any]]:
    """Transform a string like '3.8' in a list of single digits that can be used to 'naturally' sort similar strings."""
    return [
        int(text) if text.isdigit() else text.lower() for text in _nsre.split(string)
    ]
