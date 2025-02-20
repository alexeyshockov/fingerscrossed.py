import dataclasses as dc
import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional, final

DEFAULT_TRIGGERS = {
    "error": logging.ERROR,
    "exception": logging.ERROR,
    "critical": logging.CRITICAL,
    "fatal": logging.FATAL,
    "failure": logging.FATAL,
}

DEFAULT_TRIGGER_LEVEL_NAMES = frozenset(DEFAULT_TRIGGERS.keys())
DEFAULT_TRIGGER_LEVELS = frozenset(DEFAULT_TRIGGERS.values())


@dc.dataclass(slots=True)
class FingersCrossedOp:
    logger: object | Callable[..., None]
    method_name: str | None
    args: tuple
    kwargs: dict

    @property
    def target(self) -> Callable[..., None]:
        return getattr(self.logger, self.method_name) if self.method_name else self.logger


def is_error(op: FingersCrossedOp) -> bool:
    if op.args and isinstance(record := op.args[0], logging.LogRecord):
        return record.levelno in DEFAULT_TRIGGER_LEVELS
    return op.method_name in DEFAULT_TRIGGER_LEVEL_NAMES


_EMPTY_BUFFER: list[FingersCrossedOp] = []


@final
class _FingersCrossedOps:
    __slots__ = ("_buffer", "_lock", "triggers_by", "triggered")

    def __init__(self, trigger: Callable[[FingersCrossedOp], bool] = is_error):
        self._buffer: list[FingersCrossedOp] = []
        self._lock = threading.Lock()
        self.triggers_by = trigger
        self.triggered = False

    def __bool__(self):
        return not self.triggered

    def try_add(self, target, method_name, *args, **kwargs) -> bool:
        with self._lock:
            if self.triggered:
                return False
            op = FingersCrossedOp(target, method_name, args, kwargs)
            if self.triggers_by(op):
                return False
            self._buffer.append(op)
            return True

    def flush(self) -> None:
        with self._lock:
            if self.triggered:
                return
            self.triggered = True
            buffer = self._buffer
            self._buffer = _EMPTY_BUFFER

        for op in buffer:
            op.target(*op.args, **op.kwargs)


current_ops: ContextVar[Optional[_FingersCrossedOps]] = ContextVar("op_buffer", default=None)


@contextmanager
def fingers_crossed(trigger: Callable[[FingersCrossedOp], bool] = is_error) -> Iterator[None]:
    ops = _FingersCrossedOps(trigger)
    ops_token = current_ops.set(ops)
    try:
        yield
    except BaseException:
        ops.flush()
        raise
    finally:
        current_ops.reset(ops_token)
