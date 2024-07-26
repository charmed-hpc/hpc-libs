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

"""Abstractions for managing Slurm operations via snap or systemd.

This library contains manager classes that provide high-level interfaces
for managing Slurm operations within charmed operators.

### Example Usage

#### Managing the `slurmctld` service

The `SlurmctldManager` class manages the operations of the Slurm controller service.
You can pass the boolean keyword argument `snap=True` or `snap=False` to instruct
`SlurmctldManager` to either use the Slurm snap package or Debian package respectively.

```python3
from charms.hpc_libs.v0.slurm_ops import SlurmctldManager


class ApplicationCharm(CharmBase):
    # Application charm that needs to use the Slurm snap.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._slurm_manager = SlurmctldManager(snap=True)
        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, _) -> None:
        self._slurmctld.install()
        self.unit.set_workload_version(self._slurmctld.version())
        with self._slurmctld.config() as config:
            config.cluster_name = "cluster"
```
"""

__all__ = [
    "SlurmOpsError",
    "ServiceType",
    "SlurmOpsManager",
    "ServiceManager",
    "MungeKeyManager",
    "MungeManager",
    "SnapManager",
    "SlurmManagerBase",
    "SlurmctldManager",
    "SlurmdManager",
    "SlurmdbdManager",
    "SlurmrestdManager",
]

import logging
import os
import socket
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import dotenv
import yaml
from slurmutils.editors import slurmconfig, slurmdbdconfig

# The unique Charmhub library identifier, never change it
LIBID = "541fd767f90b40539cf7cd6e7db8fabf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 6

# Charm library dependencies to fetch during `charmcraft pack`.
PYDEPS = ["pyyaml>=6.0.2", "python-dotenv~=1.0.1", "slurmutils~=0.6.0"]

_logger = logging.getLogger(__name__)


def _call(cmd: str, *args: str, stdin: Optional[str] = None) -> str:
    """Call a command with logging.

    Raises:
        SlurmOpsError: Raised if the command fails.
    """
    cmd = [cmd, *args]
    _logger.debug(f"Executing command {cmd}")
    try:
        return subprocess.check_output(cmd, input=stdin, stderr=subprocess.PIPE, text=True).strip()
    except subprocess.CalledProcessError as e:
        _logger.error(f"`{' '.join(cmd)}` failed")
        _logger.error(f"stderr: {e.stderr}")
        raise SlurmOpsError(f"command {cmd[0]} failed. reason:\n{e.stderr}")


def _snap(*args) -> str:
    """Control snap by via executed `snap ...` commands.

    Raises:
        subprocess.CalledProcessError: Raised if snap command fails.
    """
    return _call("snap", *args)


class SlurmOpsError(Exception):
    """Exception raised when a slurm operation failed."""

    @property
    def message(self) -> str:
        """Return message passed as argument to exception."""
        return self.args[0]


class ServiceType(Enum):
    """Type of Slurm service to manage."""

    MUNGED = "munged"
    PROMETHEUS_EXPORTER = "slurm-prometheus-exporter"
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


class ServiceManager(ABC):
    """Control a Slurm service."""

    @abstractmethod
    def __init__(self, service: ServiceType) -> None: ...

    @abstractmethod
    def enable(self) -> None:
        """Enable service."""

    @abstractmethod
    def disable(self) -> None:
        """Disable service."""

    @abstractmethod
    def restart(self) -> None:
        """Restart service."""

    @abstractmethod
    def active(self) -> bool:
        """Return True if the service is active."""

    @property
    @abstractmethod
    def type(self) -> ServiceType:
        """Return the service type of the managed service."""


class MungeKeyManager(ABC):
    """Control the munge key."""

    @abstractmethod
    def get(self) -> str:
        """Get the current munge key.

        Returns:
            The current munge key as a base64-encoded string.
        """

    @abstractmethod
    def set(self, key: str) -> None:
        """Set a new munge key.

        Args:
            key: A new, base64-encoded munge key.
        """

    @abstractmethod
    def generate(self) -> None:
        """Generate a new, cryptographically secure munge key."""


class _EnvManager:
    """Control configuration of environment variables used in Slurm components.

    Every configuration value is automatically uppercased and prefixed with the service name.
    """

    def __init__(self, file: Union[str, os.PathLike], prefix: str) -> None:
        self._file: Path = Path(file)
        self._service = prefix

    def _config_to_env_var(self, key: str) -> str:
        """Get the environment variable corresponding to the configuration `key`."""
        return self._service.replace("-", "_").upper() + "_" + key

    def get(self, key: str) -> Optional[str]:
        """Get specific environment variable for service."""
        return dotenv.get_key(self._file, self._config_to_env_var(key))

    def set(self, config: Mapping[str, Any]) -> None:
        """Set environment variable for service."""
        for key, value in config.items():
            dotenv.set_key(self._file, self._config_to_env_var(key), str(value))

    def unset(self, key: str) -> None:
        """Unset environment variable for service."""
        dotenv.unset_key(self._file, self._config_to_env_var(key))


class SlurmOpsManager(ABC):
    """Manager to control the installation, creation and configuration of Slurm-related services."""

    @abstractmethod
    def install(self) -> None:
        """Install Slurm."""

    @abstractmethod
    def version(self) -> str:
        """Get the current version of Slurm installed on the system."""

    @property
    @abstractmethod
    def slurm_path(self) -> Path:
        """Get the path to the Slurm configuration directory."""

    @abstractmethod
    def service_manager_for(self, type: ServiceType) -> ServiceManager:
        """Return the `ServiceManager` for the specified `ServiceType`."""

    @abstractmethod
    def _env_manager_for(self, type: ServiceType) -> _EnvManager:
        """Return the `_EnvManager` for the specified `ServiceType`."""

    @abstractmethod
    def munge_key_manager(self) -> MungeKeyManager:
        """Get the `MungeKeyManager` of this operations manager."""


class MungeManager:
    """Manage `munged` service operations."""

    def __init__(self, ops_manager: SlurmOpsManager) -> None:
        self.service = ops_manager.service_manager_for(ServiceType.MUNGED)
        self.key = ops_manager.munge_key_manager()


class PrometheusExporterManager:
    """Manage `slurm-prometheus-exporter` service operations."""

    def __init__(self, ops_manager: SlurmOpsManager) -> None:
        self.service = ops_manager.service_manager_for(ServiceType.PROMETHEUS_EXPORTER)


class SlurmManagerBase:
    """Base manager for Slurm services."""

    def __init__(self, service: ServiceType, snap: bool = False) -> None:
        if not snap:
            raise SlurmOpsError("deb packaging is currently unimplemented")
        self._ops_manager = SnapManager()
        self.service = self._ops_manager.service_manager_for(service)
        self.munge = MungeManager(self._ops_manager)
        self.exporter = PrometheusExporterManager(self._ops_manager)
        self.install = self._ops_manager.install
        self.version = self._ops_manager.version

    @property
    def hostname(self) -> str:
        """The hostname where this manager is running."""
        return socket.gethostname().split(".")[0]


class SlurmctldManager(SlurmManagerBase):
    """Manager for the Slurmctld service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=ServiceType.SLURMCTLD, *args, **kwargs)
        self._config_path = self._ops_manager.slurm_path / "slurm.conf"

    @contextmanager
    def config(self) -> slurmconfig.SlurmConfig:
        """Get the config manager of slurmctld."""
        with slurmconfig.edit(self._config_path) as config:
            yield config


class SlurmdManager(SlurmManagerBase):
    """Manager for the Slurmd service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=ServiceType.SLURMD, *args, **kwargs)
        self._env_manager = self._ops_manager._env_manager_for(ServiceType.SLURMD)

    @property
    def config_server(self) -> str:
        """Get the config server address of this Slurmd node."""
        return self._env_manager.get("CONFIG_SERVER")

    @config_server.setter
    def config_server(self, addr: str) -> None:
        """Set the config server address of this Slurmd node."""
        self._env_manager.set({"CONFIG_SERVER": addr})

    @config_server.deleter
    def config_server(self) -> None:
        """Unset the config server address of this Slurmd node."""
        self._env_manager.unset("CONFIG_SERVER")


class SlurmdbdManager(SlurmManagerBase):
    """Manager for the Slurmdbd service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=ServiceType.SLURMDBD, *args, **kwargs)
        self._config_path = self._ops_manager.slurm_path / "slurmdbd.conf"

    @contextmanager
    def config(self) -> slurmdbdconfig.SlurmdbdConfig:
        """Get the config manager of slurmctld."""
        with slurmdbdconfig.edit(self._config_path) as config:
            yield config


class SlurmrestdManager(SlurmManagerBase):
    """Manager for the Slurmrestd service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=ServiceType.SLURMRESTD, *args, **kwargs)


class _SnapServiceManager(ServiceManager):
    """Control a Slurm service."""

    def __init__(self, service: ServiceType) -> None:
        self._service = service

    def enable(self) -> None:
        """Enable service."""
        _snap("start", "--enable", f"slurm.{self._service.value}")

    def disable(self) -> None:
        """Disable service."""
        _snap("stop", "--disable", f"slurm.{self._service.value}")

    def restart(self) -> None:
        """Restart service."""
        _snap("restart", f"slurm.{self._service.value}")

    def active(self) -> bool:
        """Return True if the service is active."""
        info = yaml.safe_load(_snap("info", "slurm"))
        if (services := info.get("services")) is None:
            raise SlurmOpsError("unable to retrive snap info. ensure slurm is correctly installed")

        # Assume `services` contains the service, since `ServiceManager` is not exposed as a
        # public interface for now.
        # We don't do `"active" in state` because the word "active" is also part of "inactive" :)
        return "inactive" not in services[f"slurm.{self._service.value}"]

    @property
    def type(self) -> ServiceType:
        """Return the service type of the managed service."""
        return self._service


class _SnapMungeKeyManager(MungeKeyManager):
    """Control the munge key using Snap."""

    def _mungectl(self, *args: str, stdin: Optional[str] = None) -> str:
        """Control munge via `slurm.mungectl ...`.

        Args:
            *args: Arguments to pass to `mungectl`.
            stdin: Input to pass to `mungectl` via stdin.

        Raises:
            subprocess.CalledProcessError: Raised if `mungectl` command fails.
        """
        return _call("slurm.mungectl", *args, stdin=stdin)

    def get(self) -> str:
        """Get the current munge key.

        Returns:
            The current munge key as a base64-encoded string.
        """
        return self._mungectl("key", "get")

    def set(self, key: str) -> None:
        """Set a new munge key.

        Args:
            key: A new, base64-encoded munge key.
        """
        self._mungectl("key", "set", stdin=key)

    def generate(self) -> None:
        """Generate a new, cryptographically secure munge key."""
        self._mungectl("key", "generate")


class SnapManager(SlurmOpsManager):
    """Slurm ops manager that uses Snap as its package manager."""

    def install(self) -> None:
        """Install Slurm using the `slurm` snap."""
        # FIXME: Pin slurm to the stable channel
        _snap("install", "slurm", "--channel", "latest/candidate", "--classic")

    def version(self) -> str:
        """Get the current version of the `slurm` snap installed on the system."""
        info = yaml.safe_load(_snap("info", "slurm"))
        if (ver := info.get("installed")) is None:
            raise SlurmOpsError(
                "unable to retrieve snap info. ensure slurm is correctly installed"
            )
        return ver.split(maxsplit=1)[0]

    @property
    def slurm_path(self) -> Path:
        """Get the path to the Slurm configuration directory."""
        return Path("/var/snap/slurm/common/etc/slurm")

    def service_manager_for(self, type: ServiceType) -> ServiceManager:
        """Return the `ServiceManager` for the specified `ServiceType`."""
        return _SnapServiceManager(type)

    def _env_manager_for(self, type: ServiceType) -> _EnvManager:
        """Return the `_EnvManager` for the specified `ServiceType`."""
        return _EnvManager(file="/var/snap/slurm/common/.env", prefix=type.value)

    def munge_key_manager(self) -> MungeKeyManager:
        """Get the `MungekeyManager` class of this ops manager."""
        return _SnapMungeKeyManager()
