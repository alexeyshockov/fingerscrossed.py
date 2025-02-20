from collections.abc import Callable
from functools import partial
from typing import final, cast, Any, TypeVar, Generic

from structlog.typing import WrappedLogger

from ._core import current_ops

__all__ = ["FingersCrossedLoggerFactory"]

LoggerT = TypeVar("LoggerT", bound=WrappedLogger)


@final
class FingersCrossedLogger:
    def __init__(self, target: WrappedLogger):
        """
        :param target: The logger to wrap, usually WriteLogger/BytesLogger.
        """
        self._wrapped = target

    def _proxy_or_buffer(self, method_name: str, *args, **kwargs) -> None:
        if ops := current_ops.get():
            if ops.try_add(self._wrapped, method_name, *args, **kwargs):
                return
            ops.flush()
        getattr(self._wrapped, method_name)(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(wrapped={self._wrapped!r})>"

    def __getattr__(self, method_name: str) -> Any:
        if method_name == "__deepcopy__":
            return None

        wrapped = partial(self._proxy_or_buffer, method_name)
        setattr(self, method_name, wrapped)

        return wrapped

    def __getstate__(self) -> dict[str, Any]:
        """Our __getattr__ magic makes this necessary."""
        return self.__dict__

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Our __getattr__ magic makes this necessary."""
        for k, v in state.items():
            setattr(self, k, v)


@final
class FingersCrossedLoggerFactory(Generic[LoggerT]):
    def __init__(self, target: Callable[..., LoggerT], /):
        self._wrapped_factory = target

    def __call__(self, *args) -> LoggerT:
        target = self._wrapped_factory(*args)
        return cast(LoggerT, FingersCrossedLogger(target))
