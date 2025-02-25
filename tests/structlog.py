from structlog.testing import CapturingLogger

from fingerscrossed import fingers_crossed
from fingerscrossed.structlog import FingersCrossedLogger, FingersCrossedLoggerFactory


def test_basic_logging():
    cl = CapturingLogger()
    logger = FingersCrossedLogger(cl)

    with fingers_crossed():
        logger.info("test message", x=1)
        logger.error("error message", y=2)  # Triggers emission
    
    assert len(cl.calls) == 2
    assert cl.calls[0].method_name == "info"
    assert cl.calls[0].args == ("test message",)
    assert cl.calls[0].kwargs == {"x": 1}
    assert cl.calls[1].method_name == "error"
    assert cl.calls[1].args == ("error message",)
    assert cl.calls[1].kwargs == {"y": 2}


def test_no_trigger():
    cl = CapturingLogger()
    logger = FingersCrossedLogger(cl)

    with fingers_crossed():
        logger.info("test1")
        logger.info("test2")

    assert len(cl.calls) == 0


def test_factory():
    cl = CapturingLogger()
    factory = FingersCrossedLoggerFactory(lambda: cl)
    logger = factory()

    assert isinstance(logger, FingersCrossedLogger)
    assert logger._wrapped is cl
