# Copyright 2024 Canonical Ltd.
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


"""Library to manage the Slurm snap.

This library contains the `SlurmManager` class, which offers interfaces to use and manage
the Slurm snap inside charms.

### General usage

For starters, the `SlurmManager` constructor receives a `Service` enum as a parameter, which
helps the manager determine things like the correct service to enable, or the correct settings
key to mutate.

```
from charms.hpc_libs.v0.slurm_ops import (
    Service,
    SlurmManager,
)

class ApplicationCharm(CharmBase):
    # Application charm that needs to use the Slurm snap.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Charm events defined in the NFSRequires class.
        self._slurm_manager = SlurmManager(Service.SLURMCTLD)
        self.framework.observe(
            self.on.install,
            self._on_install,
        )

    def _on_install(self, _) -> None:
        self._slurm_manager.install()
        self.unit.set_workload_version(self._slurm_manager.version())
        self._slurm_manager.set_config("cluster-name", "cluster")
```
"""

import base64
import enum
import functools
import logging
import os
import subprocess
import tempfile

import yaml

_logger = logging.getLogger(__name__)

# The unique Charmhub library identifier, never change it
LIBID = "541fd767f90b40539cf7cd6e7db8fabf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1


PYDEPS = ["pyyaml>=6.0.1"]


def _call(cmd: str, *args: [str]) -> bytes:
    """Call a command with logging.

    Raises:
        subprocess.CalledProcessError: Raised if the command fails.
    """
    cmd = [cmd, *args]
    _logger.debug(f"Executing command {cmd}")
    try:
        return subprocess.check_output(cmd, stderr=subprocess.PIPE, text=False)
    except subprocess.CalledProcessError as e:
        _logger.error(f"`{' '.join(cmd)}` failed")
        _logger.error(f"stderr: {e.stderr.decode()}")
        raise


def _snap(*args) -> str:
    """Control snap by via executed `snap ...` commands.

    Raises:
        subprocess.CalledProcessError: Raised if snap command fails.
    """
    return _call("snap", *args).decode()


_get_config = functools.partial(_snap, "get", "slurm")
_set_config = functools.partial(_snap, "set", "slurm")


class Service(enum.Enum):
    """Type of Slurm service that will be managed by `SlurmManager`."""

    SLURMD = "slurmd"
    SLURMCTLD = "slurmctld"
    SLURMDBD = "slurmdbd"
    SLURMRESTD = "slurmrestd"

    @property
    def config_name(self) -> str:
        """Configuration name on the slurm snap for this service type."""
        if self is Service.SLURMCTLD:
            return "slurm"
        return self.value


class SlurmManager:
    """Slurm snap manager.

    This class offers methods to manage the Slurm snap for a certain service type.
    The list of available services is specified by the `Service` enum.
    """

    def __init__(self, service: Service):
        self._service = service

    def install(self):
        """Install the slurm snap in this system."""
        # TODO: Pin slurm to the stable channel
        _snap("install", "slurm", "--channel", "latest/candidate", "--classic")

    def enable(self):
        """Start and enable the managed slurm service and the munged service."""
        _snap("start", "--enable", "slurm.munged")
        _snap("start", "--enable", f"slurm.{self._service.value}")

    def restart(self):
        """Restart the managed slurm service."""
        _snap("restart", f"slurm.{self._service.value}")

    def restart_munged(self):
        """Restart the munged service."""
        _snap("restart", "slurm.munged")

    def disable(self):
        """Disable the managed slurm service and the munged service."""
        _snap("stop", "--disable", "slurm.munged")
        _snap("stop", "--disable", f"slurm.{self._service.value}")

    def set_config(self, key: str, value: str):
        """Set a snap config for the managed slurm service.

        See the configuration section from the [Slurm readme](https://github.com/charmed-hpc/slurm-snap#configuration)
        for a list of all the available configurations.

        Note that this will only allow configuring the settings that are exclusive to
        the specific managed service. (the slurmctld service uses the slurm parent key)
        """
        _set_config(f"{self._service.config_name}.{key}={value}")

    def get_config(self, key: str) -> str:
        """Get a snap config for the managed slurm service.

        See the configuration section from the [Slurm readme](https://github.com/charmed-hpc/slurm-snap#configuration)
        for a list of all the available configurations.

        Note that this will only allow fetching the settings that are exclusive to
        the specific managed service. (the slurmctld service uses the slurm parent key)
        """
        # Snap returns the config value with an additional newline at the end.
        return _get_config(f"{self._service.config_name}.{key}").strip()

    def generate_munge_key(self) -> bytes:
        """Generate a new cryptographically secure munged key."""
        handle, path = tempfile.mkstemp()
        try:
            _call("mungekey", "-f", "-k", path)
            os.close(handle)
            with open(path, "rb") as f:
                return f.read()
        finally:
            os.remove(path)

    def set_munge_key(self, key: bytes):
        """Set the current munged key."""
        # TODO: use `slurm.setmungekey` when implemented
        # subprocess.run(["slurm.setmungekey"], stdin=key)
        key = base64.b64encode(key).decode()
        _set_config(f"munge.key={key}")

    def get_munge_key(self) -> bytes:
        """Get the current munged key."""
        # TODO: use `slurm.setmungekey` when implemented
        # key = subprocess.run(["slurm.getmungekey"])
        key = _get_config("munge.key")
        return base64.b64decode(key)

    def version(self) -> str:
        """Get the installed Slurm version of the snap."""
        info = yaml.safe_load(_snap("info", "slurm"))
        version: str = info["installed"]
        return version.split(maxsplit=1)[0]
