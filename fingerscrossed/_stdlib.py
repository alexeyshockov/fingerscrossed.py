from collections.abc import Collection
from contextlib import ExitStack
from logging import Handler, LogRecord, Formatter, Filter
from sys import stderr
from typing import final, TextIO, Any
from unittest.mock import patch

from ._core import current_ops, _FingersCrossedOps


@final
class FingersCrossedHandler(Handler):
    """
    Logging handler decorator to buffers log records until an error is encountered ("fingers crossed" pattern).

    See also: :class:`logging.handlers.MemoryHandler`.
    """

    @classmethod
    def wrap(cls, target: Handler, /) -> Handler:
        from logging.handlers import HTTPHandler, SocketHandler

        def has_structlog_formatter() -> bool:
            try:
                import structlog.stdlib
                return isinstance(target.formatter, structlog.stdlib.ProcessorFormatter)
            except ImportError:
                return False

        def is_otel_sdk_handler() -> bool:
            try:
                from opentelemetry.sdk._logs import LoggingHandler  # noqa
                return isinstance(target, LoggingHandler)
            except ImportError:
                return False

        def is_structlog_handler() -> bool:
            try:
                from structlog_extras.stdlib import ProcessorHandler  # noqa
                return isinstance(target, ProcessorHandler)
            except ImportError:
                return False

        pre_compute = set()
        if isinstance(target, HTTPHandler):
            pre_compute.add("mapLogRecord")
        if isinstance(target, SocketHandler):
            pre_compute.add("makePickle")
        if has_structlog_formatter():
            pre_compute.add("format")
        if is_otel_sdk_handler():
            pre_compute.add("_translate")
        if is_structlog_handler():
            pre_compute.add("process")
        return cls(target, pre_compute=pre_compute)

    def __init__(self, target: Handler, /, *, pre_compute: Collection[str] = ()):
        self._wrapped = target
        self.pre_compute = tuple(pre_compute)
        super().__init__()

        self.addFilter = target.addFilter
        self.removeFilter = target.removeFilter
        self.filter = target.filter
        self.setLevel = target.setLevel
        self.setFormatter = target.setFormatter
        self.format = target.format
        self.acquire = target.acquire
        self.release = target.release
        self.emit = target.emit
        self.handleError = target.handleError
        self.flush = target.flush

    def createLock(self):
        self.lock = self._wrapped.lock

    @property
    def level(self) -> int:
        return self._wrapped.level

    @property
    def formatter(self) -> Formatter:
        return self._wrapped.formatter

    @property
    def filters(self) -> list[Filter]:
        return self._wrapped.filters

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(wrapped={self._wrapped!r})>"

    def _handle(self, record: LogRecord, *pre_computed) -> None:
        wrapped = self._wrapped
        wrapped.acquire()
        try:
            with ExitStack() as patched:
                for meth, value in zip(self.pre_compute, pre_computed):
                    patched.enter_context(patch.object(wrapped, meth, return_value=value))
                wrapped.emit(record)
        except Exception:  # noqa
            wrapped.handleError(record)
        finally:
            wrapped.release()

    def _handle_later(self, ops: _FingersCrossedOps, record: LogRecord) -> None:
        wrapped = self._wrapped
        pre_computed = [getattr(wrapped, meth)(record) for meth in self.pre_compute]
        if ops.try_add(self._handle, None, record, *pre_computed):
            return
        ops.flush()
        self._handle(record, *pre_computed)

    # A bit optimized version of the parent (logging.Handler) method, same logic
    def handle(self, record: LogRecord) -> bool:
        wrapped = self._wrapped
        if ops := current_ops.get():
            if accepted := wrapped.filter(record):
                self._handle_later(ops, record)
            return accepted
        return wrapped.handle(record)

    def emit(self, record: LogRecord) -> None:
        if ops := current_ops.get():
            self._handle_later(ops, record)
        else:
            self._wrapped.emit(record)

    def close(self):
        super().close()
        self._wrapped.close()


@final
class FingersCrossedStreamHandler(Handler):
    """
    Optimization for the most common case.
    """

    def __init__(self, stream: TextIO | Any = stderr, /, *, formatter: Formatter | None = None):
        super().__init__()
        self.terminator = "\n"
        self._stream = stream
        self._stream_write = stream.write
        self._stream_flush = getattr(stream, "flush", None)
        self.setFormatter(formatter)

    def flush(self):
        if flush := self._stream_flush:
            with self.lock:
                flush()

    def handle(self, record: LogRecord) -> bool:
        if not self.filter(record):
            return False
        message = self.format(record)
        if ops := current_ops.get():
            if ops.try_add(self._handle, None, record, message):
                return True
            ops.flush()
        self._handle(record, message)
        return True

    def emit(self, record: LogRecord) -> None:
        self._handle(record, self.format(record))

    def _handle(self, record: LogRecord, message: str) -> None:
        try:
            with self.lock:
                self._stream_write(message + self.terminator)
                self.flush()
        except Exception:  # noqa
            self.handleError(record)
