from ._core import fingers_crossed, FingersCrossedOp
from ._stdlib import FingersCrossedHandler, FingersCrossedStreamHandler

try:
    from ._version import __version__  # noqa
except ImportError:
    __version__ = "dev"

__all__ = [
    "__version__",
    "fingers_crossed",
    "FingersCrossedOp",
    "FingersCrossedHandler",
    "FingersCrossedStreamHandler",
]

