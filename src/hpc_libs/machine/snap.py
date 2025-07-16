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

"""Classes and functions for managing operations involving `snap`/`snapd`."""

__all__ = ["SnapServiceManager", "snap"]

from subprocess import CalledProcessError
from typing import Any

import yaml

from ..errors import SnapError
from .core import ServiceManager, call


def snap(*args: str, **kwargs: Any) -> tuple[str, int]:  # noqa D417
    """Control snaps using `snap ...` commands.

    Keyword Args:
        stdin: Standard input to pipe to the `snap` command.
        check:
            If set to `True`, raise an error if the `snap` command
            exits with a non-zero exit code.

    Raises:
        SystemdError: Raised if a `snap` command fails and check is set to `True`.
    """
    try:
        result = call("snap", *args, **kwargs)
    except CalledProcessError as e:
        raise SnapError(
            f"snap command '{' '.join(e.cmd)}' failed with exit code {e.returncode}. "
            + f"reason: {e.stderr}"
        )

    return result.stdout, result.returncode


class SnapServiceManager(ServiceManager):
    """Control a service using `snap`.

    Args:
        service: Name of the service to control using `snap`
        snap: Name of the installed snap package that the service belongs.

    Notes:
        - Snap services names are typically represented as `<snap>.<service>` where `snap` is
          the name of the installed snap package, and `service` is the name of the service
          provided by the installed snap package. However, if the service name is the same as
          the installed package name, then the snap service name will be represented as just
          `service`. Because of this behavior, `snap` is an optional argument.
    """

    def __init__(self, service: str, /, snap: str | None = None) -> None:
        self._service = f"{snap}.{service}" if snap else service
        self._snap = snap if snap else service

    def start(self) -> None:
        """Start service."""
        snap("start", self._service)

    def stop(self) -> None:
        """Stop service."""
        snap("stop", self._service)

    def enable(self) -> None:
        """Enable service."""
        snap("start", "--enable", self._service)

    def disable(self) -> None:
        """Disable service."""
        snap("stop", "--disable", self._service)

    def restart(self) -> None:
        """Restart service."""
        snap("restart", self._service)

    def is_active(self) -> bool:
        """Check if service is active."""
        info = yaml.safe_load(snap("info", self._snap)[0])
        services = info.get("services")
        if services is None:
            raise SnapError(
                f"cannot retrieve '{self._service}' service info with 'snap info {self._snap}'"
            )

        # Do not check for "active" in the service's state because the
        # word "active" is also part of "inactive".
        return "inactive" not in services[self._service]
