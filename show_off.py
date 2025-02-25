import logging
from functools import partial

import anyio
from anyio import create_task_group

from fingerscrossed import fingers_crossed


def configure():
    from sys import stdout
    from fingerscrossed import FingersCrossedStreamHandler

    root_logger = logging.getLogger()
    root_logger.addHandler(FingersCrossedStreamHandler(stdout))
    root_logger.setLevel(logging.NOTSET)


logger = logging.getLogger("our.app")


async def req_middleware(request: int, call_next):
    try:
        with fingers_crossed():
            logger.debug("Request received: %d", request)
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
