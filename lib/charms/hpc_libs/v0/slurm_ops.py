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


"""Abstractions for managing Slurm operations via snap.

This library contains the `SlurmManagerBase` and `ServiceType` class
which provide high-level interfaces for managing Slurm within charmed operators.

### Example Usage

#### Managing a Slurm service

The `SlurmManagerBase` constructor receives a `ServiceType` enum. The enum instructs
the inheriting Slurm service manager how to manage its corresponding Slurm service on the host.

```python3
import charms.hpc_libs.v0.slurm_ops as slurm
from charms.hpc_libs.v0.slurm_ops import SlurmManagerBase, ServiceType

class SlurmctldManager(SlurmManagerBase):
    # Manage `slurmctld` service on host.

    def __init__(self) -> None:
        super().__init__(ServiceType.SLURMCTLD)


class ApplicationCharm(CharmBase):
    # Application charm that needs to use the Slurm snap.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Charm events defined in the NFSRequires class.
        self._slurm_manager = SlurmctldManager()
        self.framework.observe(
            self.on.install,
            self._on_install,
        )

    def _on_install(self, _) -> None:
        slurm.install()
        self.unit.set_workload_version(slurm.version())
        self._slurm_manager.config.set({"cluster-name": "cluster"})
```
"""

__all__ = [
    "install",
    "version",
    "ServiceType",
    "SlurmManagerBase",
]

import json
import logging
import subprocess
from collections.abc import Mapping
from enum import Enum
from typing import Any, Optional

import yaml

# The unique Charmhub library identifier, never change it
LIBID = "541fd767f90b40539cf7cd6e7db8fabf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

# Charm library dependencies to fetch during `charmcraft pack`.
PYDEPS = ["pyyaml>=6.0.1"]

_logger = logging.getLogger(__name__)


def install() -> None:
    """Install Slurm."""
    # FIXME: Pin slurm to the stable channel
    _snap("install", "slurm", "--channel", "latest/candidate", "--classic")


def version() -> str:
    """Get the current version of Slurm installed on the system."""
    info = yaml.safe_load(_snap("info", "slurm"))
    ver: str = info["installed"]
    return ver.split(maxsplit=1)[0]


def _call(cmd: str, *args: str, stdin: Optional[str] = None) -> str:
    """Call a command with logging.

    Raises:
        subprocess.CalledProcessError: Raised if the command fails.
    """
    cmd = [cmd, *args]
    _logger.debug(f"Executing command {cmd}")
    try:
        return subprocess.check_output(cmd, input=stdin, stderr=subprocess.PIPE, text=True).strip()
    except subprocess.CalledProcessError as e:
        _logger.error(f"`{' '.join(cmd)}` failed")
        _logger.error(f"stderr: {e.stderr.decode()}")
        raise


def _snap(*args) -> str:
    """Control snap by via executed `snap ...` commands.

    Raises:
        subprocess.CalledProcessError: Raised if snap command fails.
    """
    return _call("snap", *args)


def _mungectl(*args: str, stdin: Optional[str] = None) -> str:
    """Control munge via `slurm.mungectl ...`.

    Args:
        *args: Arguments to pass to `mungectl`.
        stdin: Input to pass to `mungectl` via stdin.

    Raises:
        subprocess.CalledProcessError: Raised if `mungectl` command fails.
    """
    return _call("slurm.mungectl", *args, stdin=stdin)


class ServiceType(Enum):
    """Type of Slurm service to manage."""

    MUNGED = "munged"
    SLURMD = "slurmd"
    SLURMCTLD = "slurmctld"
    SLURMDBD = "slurmdbd"
    SLURMRESTD = "slurmrestd"

    @property
    def config_name(self) -> str:
        """Configuration name on the slurm snap for this service type."""
        if self is ServiceType.SLURMCTLD:
            return "slurm"
        if self is ServiceType.MUNGED:
            return "munge"

        return self.value


class ServiceManager:
    """Control a Slurm service."""

    def enable(self) -> None:
        """Enable service."""
        _snap("start", "--enable", f"slurm.{self._service.value}")

    def disable(self) -> None:
        """Disable service."""
        _snap("stop", "--disable", f"slurm.{self._service.value}")

    def restart(self) -> None:
        """Restart service."""
        _snap("restart", f"slurm.{self._service.value}")


class ConfigurationManager:
    """Control configuration of a Slurm component."""

    def __init__(self, service: ServiceType) -> None:
        self._service = service

    def get_options(self, *keys: str) -> Mapping[str, Any]:
        """Get given configurations values for Slurm component."""
        configs = {}
        for key in keys:
            config = self.get(key)
            target = key.rsplit(".", maxsplit=1)[-1]
            configs[target] = config

        return configs

    def get(self, key: str) -> Any:
        """Get specific configuration value for Slurm component."""
        key = f"{self._service.config_name}.{key}"
        config = json.loads(_snap("get", "-d", "slurm", key))
        return config[key]

    def set(self, config: Mapping[str, Any]) -> None:
        """Set configuration for Slurm component."""
        args = [f"{self._service.config_name}.{k}={json.dumps(v)}" for k, v in config.items()]
        _snap("set", "slurm", *args)

    def unset(self, *keys) -> None:
        """Unset configuration for Slurm component."""
        args = [f"{self._service.config_name}.{k}!" for k in keys]
        _snap("unset", "slurm", *args)


class MungeManager(ServiceManager):
    """Manage `munged` service operations."""

    def __init__(self) -> None:
        self._service = ServiceType.MUNGED
        self.config = ConfigurationManager(ServiceType.MUNGED)

    def get_key(self) -> str:
        """Get the current munge key.

        Returns:
            The current munge key as a base64-encoded string.
        """
        return _mungectl("key", "get")

    def set_key(self, key: str) -> None:
        """Set a new munge key.

        Args:
            key: A new, base64-encoded munge key.
        """
        _mungectl("key", "set", stdin=key)

    def generate_key(self) -> None:
        """Generate a new, cryptographically secure munge key."""
        _mungectl("key", "generate")


class SlurmManagerBase(ServiceManager):
    """Base manager for Slurm services."""

    def __init__(self, service: ServiceType) -> None:
        self._service = service
        self.config = ConfigurationManager(service)
        self.munge = MungeManager()
