import signal
from contextlib import contextmanager

delayed_interrupt = False


class IsInterrupted:
    by_user = False
    delayed = False


@contextmanager
def delay_keyboard_interrupt():
    """TODO"""

    def _interrupt(_, __):
        IsInterrupted.delayed = True

    original = signal.signal(signal.SIGINT, _interrupt)
    yield
    signal.signal(signal.SIGINT, original)
    if IsInterrupted.delayed:
        raise KeyboardInterrupt


def ctrl_c_handler(_, __) -> None:
    """When ctrl-c is captured, TODO."""
    # do stuff - this is needed when ctrl-c is pressed when a c.run is executing
    IsInterrupted.by_user = True
    raise KeyboardInterrupt


def capture_signal():
    signal.signal(signal.SIGINT, ctrl_c_handler)
