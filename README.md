# Python logging, fingers crossed

[![PyPI package version](https://img.shields.io/pypi/v/fingerscrossed)](https://pypi.org/project/fingerscrossed/)
![Python versions](https://img.shields.io/pypi/pyversions/fingerscrossed)
<br>
[![Code coverage](https://img.shields.io/sonar/coverage/alexeyshockov_fingerscrossed?server=https%3A%2F%2Fsonarcloud.io)](https://sonarcloud.io/project/overview?id=alexeyshockov_fingerscrossed)

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

### Structlog (via standard logging)

It's usual to use `structlog` with the standard logging module, [rendering everything using `structlog`'s 
`ProcessorFormatter`](https://www.structlog.org/en/stable/standard-library.html#rendering-using-structlog-based-formatters-within-logging).

With this approach, the same handler decorator can be used:

```python
import logging
import structlog
from fingerscrossed import fingers_crossed, FingersCrossedStreamHandler

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
]
structlog.configure(
    processors=shared_processors + [
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    logger_factory=structlog.stdlib.LoggerFactory(),
)
stdlib_processors = [
    structlog.stdlib.add_logger_name,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.stdlib.ExtraAdder(),
]
structlog_formatter = structlog.stdlib.ProcessorFormatter(
    foreign_pre_chain=stdlib_processors + shared_processors,
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(),
    ]
)

root_logger = logging.getLogger()
root_logger.addHandler(FingersCrossedStreamHandler(formatter=structlog_formatter))
root_logger.setLevel(logging.NOTSET)

logger = structlog.get_logger("my_logger")

# Same req_handler as above
```

### Structlog (directly)

When using `structlog` directly, the `FingersCrossedLoggerFactory` can be used to decorate the real logger:

```python
import logging
import structlog
import orjson
from fingerscrossed import fingers_crossed
from fingerscrossed.structlog import FingersCrossedLoggerFactory

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(orjson.dumps),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    logger_factory=FingersCrossedLoggerFactory(structlog.BytesLoggerFactory()),
)

logger = structlog.get_logger()

# Same req_handler as above
```

###  Loguru

Loguru can use the same `FingersCrossedHandler` as the standard logging:

```python
import logging
from loguru import logger
from fingerscrossed import fingers_crossed, FingersCrossedHandler

logger.add(FingersCrossedHandler(logging.FileHandler("mylog.log")))

# Same req_handler as above
```

### OpenTelemetry SDK

TBD
