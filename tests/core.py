import logging
from logging import Handler

from structlog.testing import CapturingLogger

from fingerscrossed import fingers_crossed, FingersCrossedOp, FingersCrossedHandler
from fingerscrossed.structlog import FingersCrossedLogger


class CapturingHandler(Handler):
    def __init__(self):
        super().__init__()
        self.calls = []

    def emit(self, record):
        self.calls.append(record)


def test_custom_trigger():
    cl = CapturingLogger()
    logger = FingersCrossedLogger(cl)

    def custom_trigger(op: FingersCrossedOp) -> bool:
        return "trigger" in str(op.args)

    with fingers_crossed(custom_trigger):
        logger.info("just a message")
        logger.info("trigger message")
    
    assert len(cl.calls) == 2
    assert cl.calls[0].method_name == "info"
    assert cl.calls[0].args == ("just a message",)
    assert cl.calls[1].method_name == "info"
    assert cl.calls[1].args == ("trigger message",)


def test_combined():
    """Test that stdlib logging and structlog work together in the same fingers_crossed context."""
    cl = CapturingLogger()
    structlog_logger = FingersCrossedLogger(cl)

    ch = CapturingHandler()
    handler = FingersCrossedHandler(ch)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    stdlib_logger = logging.getLogger("our.app")

    # Test both loggers in the same context
    with fingers_crossed():
        structlog_logger.info("structlog message 1")
        stdlib_logger.info("stdlib message 1")

        # Nothing is propagated yet
        assert len(cl.calls) == 0
        assert len(ch.calls) == 0

        structlog_logger.error("structlog error")

        # Error triggers the buffer, all the logs should be flushed
        assert len(cl.calls) == 2
        assert len(ch.calls) == 1

        stdlib_logger.info("stdlib message 2")
        structlog_logger.info("structlog message 2")

    assert len(cl.calls) == 3
    assert len(ch.calls) == 2
