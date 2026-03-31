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

"""Logging utilities."""

__all__ = ["setup_logging"]

import logging
import pprint


class _PrettyFormatter(logging.Formatter):
    """Pretty print dictionaries in logging messages."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            record.msg = pprint.pformat(record.msg)
        elif record.args:
            # Handle cases like: logger.debug("data: %s", my_dict)
            record.args = tuple(
                pprint.pformat(arg) if isinstance(arg, dict) else arg
                for arg in (record.args if isinstance(record.args, tuple) else (record.args,))
            )

        return super().format(record)


def setup_logging(name: str | None = None) -> logging.Logger:
    """Set up logging.

    Args:
        name: Name of logger to return. If `None`, return the root logger.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_PrettyFormatter())

    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger
