import logging
from functools import partial

import anyio
import structlog
from anyio import create_task_group
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger

from fingerscrossed import fingers_crossed


def configure():
    """
    Configure structlog to sink everything to standard library logging, as per
    https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging,
    and wrap the final logging handler.
    """
    from sys import stdout
    from fingerscrossed import FingersCrossedStreamHandler

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    stdlib_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
    ]
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=stdlib_processors + shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ]
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(FingersCrossedStreamHandler(stdout, formatter=structlog_formatter))
    root_logger.setLevel(logging.NOTSET)


# logger = logging.getLogger("our.app")
logger: FilteringBoundLogger = structlog.get_logger("our.app")


async def req_middleware(request: int, call_next):
    try:
        with bound_contextvars(request=request), fingers_crossed():
            logger.debug("Request received")
            await call_next(request)
            logger.debug("Request processed")
    except Exception as e:
        logger.exception("Request failed", exc_info=e)


async def req_handler(request: int):
    if request >= 10:
        # Triggers all the request logs to be flushed
        raise ValueError("Very high number")
    if request >= 5:
        # Also triggers all the request logs to be flushed
        logger.error("High number")
    await anyio.sleep(request / 10)


async def main():
    req_pipeline = req_handler
    req_pipeline = partial(req_middleware, call_next=req_pipeline)
    async with create_task_group() as tg:
        for i in [1, 2, 3, 4, 5, 10]:
            tg.start_soon(req_pipeline, i)


if __name__ == "__main__":
    configure()
    anyio.run(main)
