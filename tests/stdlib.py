from logging import LogRecord, Handler, DEBUG, INFO
from unittest.mock import Mock

from fingerscrossed import FingersCrossedHandler
from fingerscrossed import fingers_crossed


def test_wrapped_filter_always_called():
    wrapped_filter = Mock(return_value=True)
    wrapped_emit = Mock()
    mock_handler = Mock(spec=Handler)
    mock_handler.filter = wrapped_filter
    mock_handler.emit = wrapped_emit
    
    wrapped = FingersCrossedHandler(mock_handler)
    rec1 = LogRecord("test", DEBUG, "test.py", 1, "debug message", (), None)
    rec2 = LogRecord("test", INFO, "test.py", 1, "info message", (), None)
    
    with fingers_crossed():
        wrapped.handle(rec1)
        wrapped_filter.assert_called_with(rec1)
        wrapped.handle(rec2)
        wrapped_filter.assert_called_with(rec2)
    # No flush, no errors in the transaction

    # As there is no flush, the emit() should not be called
    assert wrapped_emit.call_count == 0
    assert wrapped_filter.call_count == 2


def test_wrapped_format_always_called():
    wrapped_format = Mock(return_value="formatted message")
    wrapped_emit = Mock()
    mock_handler = Mock(spec=Handler)
    mock_handler.format = wrapped_format
    mock_handler.emit = wrapped_emit
    
    wrapped = FingersCrossedHandler(mock_handler, pre_compute=("format",))
    rec = LogRecord("test", INFO, "test.py", 1, "test message", (), None)
    
    with fingers_crossed():
        wrapped.handle(rec)
    # No flush, no errors in the transaction

    # As there is no flush, the emit() should not be called
    assert wrapped_emit.call_count == 0

    assert wrapped_format.call_count == 1
    wrapped_format.assert_called_once_with(rec)
