import re
import signal
from contextlib import contextmanager
from typing import Any, AnyStr, Generator, List, Pattern

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


def natural_sort_key(
    string: str, _nsre: Pattern[str] = re.compile("([0-9]+)")
) -> List[str]:
    """Transform a string like '3.8' in a list of single digits that can be used to 'naturally' sort similar strings."""
    return [
        int(text) if text.isdigit() else text.lower() for text in _nsre.split(string)
    ]
