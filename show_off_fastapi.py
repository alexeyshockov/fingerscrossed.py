import logging

import anyio
import structlog
from fastapi import FastAPI, Request
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger

from fingerscrossed import fingers_crossed
from show_off import configure

# logger = logging.getLogger("our.app")
logger: FilteringBoundLogger = structlog.get_logger("our.app")


# See https://fastapi.tiangolo.com/tutorial/middleware/
app = FastAPI()


@app.middleware("http")
async def add_req_info(request: Request, call_next):
    req_info = {
        "http.req.method": request.method,
        "http.req.path": request.url.path,
    }
    with bound_contextvars(**req_info), fingers_crossed():
        logger.debug("Request received")
        response = await call_next(request)
        logger.debug("Request processed")
        return response


@app.get("/")
async def awaiter(req_sec: float = 1):
    if req_sec >= 1:
        # Triggers all the request logs to be flushed
        raise ValueError("Very high number")
    if req_sec >= 0.5:
        # Also triggers all the request logs to be flushed
        logger.error("High number")
    await anyio.sleep(req_sec)
    return f'Awaited {req_sec}, world!'


if __name__ == "__main__":
    import uvicorn

    configure()
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    uvicorn.run(app, log_config=None)
