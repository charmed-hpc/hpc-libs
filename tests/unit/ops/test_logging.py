# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for logging utilities."""

import logging
import pprint
from typing import Any

import pytest
from pytest import CaptureFixture

from charmed_hpc_libs import setup_logging
from charmed_hpc_libs.ops.logging import _PrettyFormatter  # noqa


@pytest.fixture(scope="class")
def formatter() -> _PrettyFormatter:
    """Return a `_PrettyFormatter` instance."""
    return _PrettyFormatter()


def make_log_record(msg: Any, args: tuple[Any] | None = None) -> logging.LogRecord:
    """Create a `LogRecord` with the given message and args."""
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg=msg,
        args=args,
        exc_info=None,
    )

    return record


class TestPrettyFormatter:
    """Tests for `_PrettyFormatter`.

    Ensure that logged dictionaries are beautified!
    """

    def test_format_plain_string(self, formatter) -> None:
        """Formatter passes through plain string messages unchanged."""
        result = formatter.format(make_log_record("hello world"))
        assert result == "hello world"

    def test_format_dict_message(self, formatter) -> None:
        """Formatter pretty-prints a dict message."""
        data = {"key": "value", "number": 42}
        result = formatter.format(make_log_record(data))
        assert result == pprint.pformat(data)

    def test_format_nested_dict_message(self, formatter) -> None:
        """Formatter pretty-prints a nested dict message."""
        data = {"outer": {"inner": {"deep": [1, 2, 3]}}}
        result = formatter.format(make_log_record(data))
        assert result == pprint.pformat(data)

    def test_format_dict_in_tuple_args(self, formatter) -> None:
        """Formatter pretty-prints dict args passed as a tuple."""
        data = {"key": "value"}
        result = formatter.format(make_log_record("data: %s", (data,)))
        assert pprint.pformat(data) in result

    def test_format_mixed_tuple_args(self, formatter) -> None:
        """Formatter only pretty-prints dict args within a tuple, leaving others intact."""
        data = {"key": "value"}
        result = formatter.format(make_log_record("name=%s data=%s", ("foo", data)))
        assert "foo" in result
        assert pprint.pformat(data) in result

    def test_format_non_dict_tuple_args(self, formatter) -> None:
        """Formatter leaves non-dict args unchanged."""
        result = formatter.format(make_log_record("count=%s name=%s", (42, "bar")))
        assert result == "count=42 name=bar"

    def test_format_dict_in_non_tuple_args(self, formatter) -> None:
        """Formatter pretty-prints a dict arg when args is not a tuple (single arg)."""
        data = {"key": "value"}
        # LogRecord.__init__ rejects a bare dict as args, so set it after construction.
        record = make_log_record("data: %s")
        record.args = data
        result = formatter.format(record)
        assert pprint.pformat(data) in result

    def test_format_non_dict_non_tuple_args(self, formatter) -> None:
        """Formatter leaves a non-dict single arg unchanged."""
        # LogRecord.__init__ rejects a bare int as args, so set it after construction.
        record = make_log_record("count: %s")
        record.args = 42
        result = formatter.format(record)
        assert result == "count: 42"


class TestSetupLogging:
    """Tests for `setup_logging`."""

    def test_returns_named_logger(self) -> None:
        """`setup_logging` returns a logger with the given name."""
        logger = setup_logging("test.named")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.named"

    def test_returns_root_logger(self) -> None:
        """`setup_logging` returns the root logger when name is None."""
        logger = setup_logging(None)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "root"

    def test_handler_uses_pretty_formatter(self) -> None:
        """The handler added by `setup_logging` uses `_PrettyFormatter`."""
        logger = setup_logging("test.formatter_check")
        pretty_handlers = [h for h in logger.handlers if isinstance(h.formatter, _PrettyFormatter)]
        assert len(pretty_handlers) >= 1

    def test_handler_is_stream_handler(self) -> None:
        """The handler added by `setup_logging` is a `StreamHandler`."""
        logger = setup_logging("test.handler_type")
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_logger_pretty_prints_dict(self, capfd: CaptureFixture[str]) -> None:
        """End-to-end: a dict message is pretty-printed by the logger."""
        logger = setup_logging("test.e2e_dict")
        logger.setLevel(logging.DEBUG)
        data = {"alpha": 1, "beta": 2}
        logger.debug(data)
        captured = capfd.readouterr()
        assert pprint.pformat(data) in captured.err

    def test_logger_pretty_prints_dict_arg(self, capfd: CaptureFixture[str]) -> None:
        """End-to-end: a dict passed as an arg is pretty-printed by the logger."""
        logger = setup_logging("test.e2e_dict_arg")
        logger.setLevel(logging.DEBUG)
        data = {"gamma": 3}
        logger.debug("payload: %s", data)
        captured = capfd.readouterr()
        assert pprint.pformat(data) in captured.err
