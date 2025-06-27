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

"""Common errors raised by functions and methods in the `hpc_libs` package."""


class Error(Exception):
    """Base error used to compose other errors."""

    @property
    def message(self) -> str:
        """Return message passed as first argument to error."""
        return self.args[0]


class SnapError(Error):
    """Error raised if a `snap`-related operation fails."""


class SystemdError(Error):
    """Error raised if a `systemd`-related operation fails."""
