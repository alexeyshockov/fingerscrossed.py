# Python logging, fingers crossed

A custom sink for [Python standard logging](https://docs.python.org/3/library/logging.html) /
[structlog](https://github.com/hynek/structlog) / [loguru](https://github.com/delgan/loguru) to buffer the logs inside
a transaction and only write them if something goes wrong ("fingers crossed" pattern).

## Installation

```shell
pip install fingerscrossed
```

## Usage

### Python standard logging

```python
import logging
from fingerscrossed import fingers_crossed, FingersCrossedHandler

root_logger = logging.getLogger()
root_logger.addHandler(FingersCrossedHandler(logging.FileHandler("mylog.log")))
root_logger.setLevel(logging.NOTSET)

logger = logging.getLogger("my_logger")


def req_handler(n: int):
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    if n % 2 == 0:
        logger.warning("This is a warning, does not trigger (flush the fingers crossed buffer)")
    else:
        logger.error("This is an error, flushes the fingers crossed buffer")


logger.info("Starting the requests")
for i in range(5):
    with fingers_crossed():
        req_handler(i)
logger.info("Finished")
```
