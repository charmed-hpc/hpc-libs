# Copyright 2025 Canonical Ltd.
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

"""Manage environment variables."""

__all__ = ["EnvManager"]

from collections.abc import Mapping
from os import PathLike
from pathlib import Path
from typing import Any

import dotenv


class EnvManager:
    """Manage environment variables in an environment file.

    Notes:
        - Environment variables are automatically uppercased.
    """

    def __init__(self, file: str | PathLike) -> None:
        self._file = file

    def get(self, key: str, /) -> str | None:
        """Get value of an environment variable in the environment file."""
        return dotenv.get_key(self._file, key.upper())

    def set(self, config: Mapping[str, Any], /, quote: bool = True) -> None:
        """Set environment variables in the environment file."""
        for key, value in config.items():
            dotenv.set_key(
                self._file, key.upper(), str(value), quote_mode="always" if quote else "never"
            )

    def unset(self, key: str, /) -> None:
        """Unset an environment variable in the environment file."""
        dotenv.unset_key(self._file, key.upper())

    @property
    def path(self) -> Path:
        """Get path to the environment file."""
        return Path(self._file)
