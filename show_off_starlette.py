import logging

import anyio
import structlog
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from structlog.contextvars import bound_contextvars
from structlog.typing import FilteringBoundLogger

from fingerscrossed import fingers_crossed
from show_off import configure

# logger = logging.getLogger("our.app")
logger: FilteringBoundLogger = structlog.get_logger("our.app")


# See https://www.starlette.io/middleware/#basehttpmiddleware
class ReqInfoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_info = {
            "http.req.method": request.method,
            "http.req.path": request.url.path,
        }
        with bound_contextvars(**req_info), fingers_crossed():
            logger.debug("Request received")
            response = await call_next(request)
            logger.debug("Request processed")
            return response


async def awaiter(request: Request):
    req_sec = float(request.query_params.get("sec", "1"))
    if req_sec >= 1:
        # Triggers all the request logs to be flushed
        raise ValueError("Very high number")
    if req_sec >= 0.5:
        # Also triggers all the request logs to be flushed
        logger.error("High number")
    await anyio.sleep(req_sec)
    return PlainTextResponse(f'Awaited {req_sec}, world!')


app = Starlette(
    routes=[Route("/", awaiter)],
    middleware=[Middleware(ReqInfoMiddleware)]
)


if __name__ == "__main__":
    import uvicorn

    configure()
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    uvicorn.run(app, log_config=None)
