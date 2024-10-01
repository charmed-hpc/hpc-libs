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

### Note

This charm library depends on the `charms.operator_libs_linux.v0.apt` charm library, which can
be imported by running `charmcraft fetch-lib charms.operator_libs_linux.v0.apt`.

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
    "SlurmctldManager",
    "SlurmdManager",
    "SlurmdbdManager",
    "SlurmrestdManager",
]

import logging
import os
import socket
import subprocess
import textwrap
from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import distro
import dotenv
import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from slurmutils.editors import cgroupconfig, slurmconfig, slurmdbdconfig
from slurmutils.models import CgroupConfig, SlurmConfig, SlurmdbdConfig

try:
    import charms.operator_libs_linux.v0.apt as apt
except ImportError as e:
    raise ImportError(
        "`slurm_ops` requires the `charms.operator_libs_linux.v0.apt` charm library to work",
        name=e.name,
        path=e.path,
    )

# The unique Charmhub library identifier, never change it
LIBID = "541fd767f90b40539cf7cd6e7db8fabf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 7

# Charm library dependencies to fetch during `charmcraft pack`.
PYDEPS = [
    "cryptography~=43.0.1",
    "pyyaml>=6.0.2",
    "python-dotenv~=1.0.1",
    "slurmutils~=0.7.0",
    "distro~=1.9.0",
]

_logger = logging.getLogger(__name__)


class SlurmOpsError(Exception):
    """Exception raised when a slurm operation failed."""

    @property
    def message(self) -> str:
        """Return message passed as argument to exception."""
        return self.args[0]


def _call(
    cmd: str, *args: str, stdin: Optional[str] = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Call a command with logging.

    If the `check` argument is set to `False`, the command call will not raise an error if the command
    fails.

    Raises:
        SlurmOpsError: Raised if the command fails.
    """
    cmd = [cmd, *args]
    _logger.debug(f"executing command {cmd}")

    result = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if result.returncode != 0:
        _logger.error(f"command {cmd} failed with message {result.stderr}")
        if check:
            raise SlurmOpsError(f"command {cmd} failed. stderr:\n{result.stderr}")

    return subprocess.CompletedProcess(
        args=result.args,
        stdout=result.stdout.strip() if result.stdout else None,
        stderr=result.stderr.strip() if result.stderr else None,
        returncode=result.returncode,
    )


def _snap(*args) -> str:
    """Control snap by via executed `snap ...` commands.

    Raises:
        SlurmOpsError: Raised if snap command fails.
    """
    return _call("snap", *args).stdout


def _systemctl(*args) -> str:
    """Control systemd units via `systemctl ...` commands.

    Raises:
        SlurmOpsError: Raised if systemctl command fails.
    """
    return _call("systemctl", *args).stdout


def _mungectl(*args, stdin: Optional[str] = None) -> str:
    """Control munge via `mungectl ...` commands.

    Raises:
        SlurmOpsError: Raised if mungectl command fails.
    """
    return _call("mungectl", *args, stdin=stdin).stdout


class _ServiceType(Enum):
    """Type of Slurm service to manage."""

    MUNGED = "munged"
    PROMETHEUS_EXPORTER = "prometheus-slurm-exporter"
    SLURMD = "slurmd"
    SLURMCTLD = "slurmctld"
    SLURMDBD = "slurmdbd"
    SLURMRESTD = "slurmrestd"

    @property
    def config_name(self) -> str:
        """Configuration name on the slurm snap for this service type."""
        if self is _ServiceType.SLURMCTLD:
            return "slurm"
        if self is _ServiceType.MUNGED:
            return "munge"

        return self.value


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


class _ConfigManager(ABC):
    """Control a Slurm configuration file."""

    def __init__(self, config_path: Union[str, Path]) -> None:
        self._config_path = config_path

    @abstractmethod
    def load(self):
        """Load the current configuration from the configuration file."""

    @abstractmethod
    def dump(self, config) -> None:
        """Dump new configuration into configuration file.

        Notes:
            Overwrites current configuration file. If just updating the
            current configuration, use `edit` instead.
        """

    @contextmanager
    @abstractmethod
    def edit(self):
        """Edit the current configuration file."""


class _SlurmConfigManager(_ConfigManager):
    """Control the `slurm.conf` configuration file."""

    def load(self) -> SlurmConfig:
        """Load the current `slurm.conf` configuration file."""
        return slurmconfig.load(self._config_path)

    def dump(self, config: SlurmConfig) -> None:
        """Dump new configuration into `slurm.conf` configuration file."""
        slurmconfig.dump(config, self._config_path)

    @contextmanager
    def edit(self) -> SlurmConfig:
        """Edit the current `slurm.conf` configuration file."""
        with slurmconfig.edit(self._config_path) as config:
            yield config


class _CgroupConfigManager(_ConfigManager):
    """Control the `cgroup.conf` configuration file."""

    def load(self) -> CgroupConfig:
        """Load the current `cgroup.conf` configuration file."""
        return cgroupconfig.load(self._config_path)

    def dump(self, config: CgroupConfig) -> None:
        """Dump new configuration into `cgroup.conf` configuration file."""
        cgroupconfig.dump(config, self._config_path)

    @contextmanager
    def edit(self) -> CgroupConfig:
        """Edit the current `cgroup.conf` configuration file."""
        with cgroupconfig.edit(self._config_path) as config:
            yield config


class _SlurmdbdConfigManager(_ConfigManager):
    """Control the `slurmdbd.conf` configuration file."""

    def load(self) -> SlurmdbdConfig:
        """Load the current `slurmdbd.conf` configuration file."""
        return slurmdbdconfig.load(self._config_path)

    def dump(self, config: SlurmdbdConfig) -> None:
        """Dump new configuration into `slurmdbd.conf` configuration file."""
        slurmdbdconfig.dump(config, self._config_path)

    @contextmanager
    def edit(self) -> SlurmdbdConfig:
        """Edit the current `slurmdbd.conf` configuration file."""
        with slurmdbdconfig.edit(self._config_path) as config:
            yield config


class _ServiceManager(ABC):
    """Control a Slurm service."""

    def __init__(self, service: _ServiceType) -> None:
        self._service = service

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
    def type(self) -> _ServiceType:
        """Return the service type of the managed service."""
        return self._service


class _SystemctlServiceManager(_ServiceManager):
    """Control a Slurm service using systemctl services."""

    def enable(self) -> None:
        """Enable service.

        Raises:
            SlurmOpsError: Raised if `systemctl enable ...` returns a non-zero returncode.
        """
        _systemctl("enable", "--now", self._service.value)

    def disable(self) -> None:
        """Disable service."""
        _systemctl("disable", "--now", self._service.value)

    def restart(self) -> None:
        """Restart service."""
        _systemctl("reload-or-restart", self._service.value)

    def active(self) -> bool:
        """Return True if the service is active."""
        return (
            _call("systemctl", "is-active", "--quiet", self._service.value, check=False).returncode
            == 0
        )


class _SnapServiceManager(_ServiceManager):
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

    def active(self) -> bool:
        """Return True if the service is active."""
        info = yaml.safe_load(_snap("info", "slurm"))
        if (services := info.get("services")) is None:
            raise SlurmOpsError("unable to retrive snap info. ensure slurm is correctly installed")

        # Assume `services` contains the service, since `ServiceManager` is not exposed as a
        # public interface for now.
        # We don't do `"active" in state` because the word "active" is also part of "inactive" :)
        return "inactive" not in services[f"slurm.{self._service.value}"]


class _OpsManager(ABC):
    """Manager to control the installation, creation and configuration of Slurm-related services."""

    @abstractmethod
    def install(self) -> None:
        """Install Slurm."""

    @abstractmethod
    def version(self) -> str:
        """Get the current version of Slurm installed on the system."""

    @property
    @abstractmethod
    def etc_path(self) -> Path:
        """Get the path to the Slurm configuration directory."""

    @property
    @abstractmethod
    def var_lib_path(self) -> Path:
        """Get the path to the Slurm variable state data directory."""

    @abstractmethod
    def service_manager_for(self, type: _ServiceType) -> _ServiceManager:
        """Return the `ServiceManager` for the specified `ServiceType`."""

    @abstractmethod
    def _env_manager_for(self, type: _ServiceType) -> _EnvManager:
        """Return the `_EnvManager` for the specified `ServiceType`."""


class _SnapManager(_OpsManager):
    """Slurm ops manager that uses Snap as its package manager."""

    def install(self) -> None:
        """Install Slurm using the `slurm` snap."""
        # FIXME: Pin slurm to the stable channel
        _snap("install", "slurm", "--channel", "latest/candidate", "--classic")
        # FIXME: Request automatic alias for `mungectl` so that we don't need to do this manually
        _snap("alias", "slurm.mungectl", "mungectl")

    def version(self) -> str:
        """Get the current version of the `slurm` snap installed on the system."""
        info = yaml.safe_load(_snap("info", "slurm"))
        if (ver := info.get("installed")) is None:
            raise SlurmOpsError(
                "unable to retrieve snap info. ensure slurm is correctly installed"
            )
        return ver.split(maxsplit=1)[0]

    @property
    def etc_path(self) -> Path:
        """Get the path to the Slurm configuration directory."""
        return Path("/var/snap/slurm/common/etc/slurm")

    @property
    def var_lib_path(self) -> Path:
        """Get the path to the Slurm variable state data directory."""
        return Path("/var/snap/slurm/common/var/lib/slurm")

    def service_manager_for(self, type: _ServiceType) -> _ServiceManager:
        """Return the `ServiceManager` for the specified `ServiceType`."""
        return _SnapServiceManager(type)

    def _env_manager_for(self, type: _ServiceType) -> _EnvManager:
        """Return the `_EnvManager` for the specified `ServiceType`."""
        return _EnvManager(file="/var/snap/slurm/common/.env", prefix=type.value)


class _AptManager(_OpsManager):
    """Slurm ops manager that uses apt as its package manager.

    Notes:
        This manager provides some environment variables that are automatically passed to the
        services with a systemctl override file. If you need to override the ExecStart parameter,
        ensure the new command correctly passes the environment variable to the command.
    """

    def __init__(self, service: _ServiceType) -> None:
        self._service_name = service.value
        self._env_file = Path(f"/etc/default/{self._service_name}")

    def install(self) -> None:
        """Install Slurm using the `slurm` snap."""
        slurm_wlm = apt.DebianRepository(
            enabled=True,
            repotype="deb",
            uri="https://ppa.launchpadcontent.net/ubuntu-hpc/slurm-wlm-23.02/ubuntu",
            release=distro.codename(),
            groups=["main"],
        )
        slurm_wlm.import_key(
            textwrap.dedent(
                """
                -----BEGIN PGP PUBLIC KEY BLOCK-----
                Comment: Hostname:
                Version: Hockeypuck 2.2

                xsFNBGTuZb8BEACtJ1CnZe6/hv84DceHv+a54y3Pqq0gqED0xhTKnbj/E2ByJpmT
                NlDNkpeITwPAAN1e3824Me76Qn31RkogTMoPJ2o2XfG253RXd67MPxYhfKTJcnM3
                CEkmeI4u2Lynh3O6RQ08nAFS2AGTeFVFH2GPNWrfOsGZW03Jas85TZ0k7LXVHiBs
                W6qonbsFJhshvwC3SryG4XYT+z/+35x5fus4rPtMrrEOD65hij7EtQNaE8owuAju
                Kcd0m2b+crMXNcllWFWmYMV0VjksQvYD7jwGrWeKs+EeHgU8ZuqaIP4pYHvoQjag
                umqnH9Qsaq5NAXiuAIAGDIIV4RdAfQIR4opGaVgIFJdvoSwYe3oh2JlrLPBlyxyY
                dayDifd3X8jxq6/oAuyH1h5K/QLs46jLSR8fUbG98SCHlRmvozTuWGk+e07ALtGe
                sGv78ToHKwoM2buXaTTHMwYwu7Rx8LZ4bZPHdersN1VW/m9yn1n5hMzwbFKy2s6/
                D4Q2ZBsqlN+5aW2q0IUmO+m0GhcdaDv8U7RVto1cWWPr50HhiCi7Yvei1qZiD9jq
                57oYZVqTUNCTPxi6NeTOdEc+YqNynWNArx4PHh38LT0bqKtlZCGHNfoAJLPVYhbB
                b2AHj9edYtHU9AAFSIy+HstET6P0UDxy02IeyE2yxoUBqdlXyv6FL44E+wARAQAB
                zRxMYXVuY2hwYWQgUFBBIGZvciBVYnVudHUgSFBDwsGOBBMBCgA4FiEErocSHcPk
                oLD4H/Aj9tDF1ca+s3sFAmTuZb8CGwMFCwkIBwIGFQoJCAsCBBYCAwECHgECF4AA
                CgkQ9tDF1ca+s3sz3w//RNawsgydrutcbKf0yphDhzWS53wgfrs2KF1KgB0u/H+u
                6Kn2C6jrVM0vuY4NKpbEPCduOj21pTCepL6PoCLv++tICOLVok5wY7Zn3WQFq0js
                Iy1wO5t3kA1cTD/05v/qQVBGZ2j4DsJo33iMcQS5AjHvSr0nu7XSvDDEE3cQE55D
                87vL7lgGjuTOikPh5FpCoS1gpemBfwm2Lbm4P8vGOA4/witRjGgfC1fv1idUnZLM
                TbGrDlhVie8pX2kgB6yTYbJ3P3kpC1ZPpXSRWO/cQ8xoYpLBTXOOtqwZZUnxyzHh
                gM+hv42vPTOnCo+apD97/VArsp59pDqEVoAtMTk72fdBqR+BB77g2hBkKESgQIEq
                EiE1/TOISioMkE0AuUdaJ2ebyQXugSHHuBaqbEC47v8t5DVN5Qr9OriuzCuSDNFn
                6SBHpahN9ZNi9w0A/Yh1+lFfpkVw2t04Q2LNuupqOpW+h3/62AeUqjUIAIrmfeML
                IDRE2VdquYdIXKuhNvfpJYGdyvx/wAbiAeBWg0uPSepwTfTG59VPQmj0FtalkMnN
                ya2212K5q68O5eXOfCnGeMvqIXxqzpdukxSZnLkgk40uFJnJVESd/CxHquqHPUDE
                fy6i2AnB3kUI27D4HY2YSlXLSRbjiSxTfVwNCzDsIh7Czefsm6ITK2+cVWs0hNQ=
                =cs1s
                -----END PGP PUBLIC KEY BLOCK-----
                """
            )
        )

        experimental = apt.DebianRepository(
            enabled=True,
            repotype="deb",
            uri="https://ppa.launchpadcontent.net/ubuntu-hpc/experimental/ubuntu",
            release=distro.codename(),
            groups=["main"],
        )
        experimental.import_key(
            textwrap.dedent(
                """
                -----BEGIN PGP PUBLIC KEY BLOCK-----
                Comment: Hostname:
                Version: Hockeypuck 2.2

                xsFNBGTuZb8BEACtJ1CnZe6/hv84DceHv+a54y3Pqq0gqED0xhTKnbj/E2ByJpmT
                NlDNkpeITwPAAN1e3824Me76Qn31RkogTMoPJ2o2XfG253RXd67MPxYhfKTJcnM3
                CEkmeI4u2Lynh3O6RQ08nAFS2AGTeFVFH2GPNWrfOsGZW03Jas85TZ0k7LXVHiBs
                W6qonbsFJhshvwC3SryG4XYT+z/+35x5fus4rPtMrrEOD65hij7EtQNaE8owuAju
                Kcd0m2b+crMXNcllWFWmYMV0VjksQvYD7jwGrWeKs+EeHgU8ZuqaIP4pYHvoQjag
                umqnH9Qsaq5NAXiuAIAGDIIV4RdAfQIR4opGaVgIFJdvoSwYe3oh2JlrLPBlyxyY
                dayDifd3X8jxq6/oAuyH1h5K/QLs46jLSR8fUbG98SCHlRmvozTuWGk+e07ALtGe
                sGv78ToHKwoM2buXaTTHMwYwu7Rx8LZ4bZPHdersN1VW/m9yn1n5hMzwbFKy2s6/
                D4Q2ZBsqlN+5aW2q0IUmO+m0GhcdaDv8U7RVto1cWWPr50HhiCi7Yvei1qZiD9jq
                57oYZVqTUNCTPxi6NeTOdEc+YqNynWNArx4PHh38LT0bqKtlZCGHNfoAJLPVYhbB
                b2AHj9edYtHU9AAFSIy+HstET6P0UDxy02IeyE2yxoUBqdlXyv6FL44E+wARAQAB
                zRxMYXVuY2hwYWQgUFBBIGZvciBVYnVudHUgSFBDwsGOBBMBCgA4FiEErocSHcPk
                oLD4H/Aj9tDF1ca+s3sFAmTuZb8CGwMFCwkIBwIGFQoJCAsCBBYCAwECHgECF4AA
                CgkQ9tDF1ca+s3sz3w//RNawsgydrutcbKf0yphDhzWS53wgfrs2KF1KgB0u/H+u
                6Kn2C6jrVM0vuY4NKpbEPCduOj21pTCepL6PoCLv++tICOLVok5wY7Zn3WQFq0js
                Iy1wO5t3kA1cTD/05v/qQVBGZ2j4DsJo33iMcQS5AjHvSr0nu7XSvDDEE3cQE55D
                87vL7lgGjuTOikPh5FpCoS1gpemBfwm2Lbm4P8vGOA4/witRjGgfC1fv1idUnZLM
                TbGrDlhVie8pX2kgB6yTYbJ3P3kpC1ZPpXSRWO/cQ8xoYpLBTXOOtqwZZUnxyzHh
                gM+hv42vPTOnCo+apD97/VArsp59pDqEVoAtMTk72fdBqR+BB77g2hBkKESgQIEq
                EiE1/TOISioMkE0AuUdaJ2ebyQXugSHHuBaqbEC47v8t5DVN5Qr9OriuzCuSDNFn
                6SBHpahN9ZNi9w0A/Yh1+lFfpkVw2t04Q2LNuupqOpW+h3/62AeUqjUIAIrmfeML
                IDRE2VdquYdIXKuhNvfpJYGdyvx/wAbiAeBWg0uPSepwTfTG59VPQmj0FtalkMnN
                ya2212K5q68O5eXOfCnGeMvqIXxqzpdukxSZnLkgk40uFJnJVESd/CxHquqHPUDE
                fy6i2AnB3kUI27D4HY2YSlXLSRbjiSxTfVwNCzDsIh7Czefsm6ITK2+cVWs0hNQ=
                =cs1s
                -----END PGP PUBLIC KEY BLOCK-----
                """
            )
        )

        repositories = apt.RepositoryMapping()
        repositories.add(slurm_wlm)
        repositories.add(experimental)

        try:
            apt.update()
            apt.add_package([self._service_name, "mungectl", "prometheus-slurm-exporter"])
        except apt.PackageNotFoundError as e:
            raise SlurmOpsError(f"failed to install {self._service_name}. reason: {e}")
        except apt.PackageError as e:
            raise SlurmOpsError(f"failed to install {self._service_name}. reason: {e}")

        self._env_file.touch(exist_ok=True)
        # Debian package postinst hook does not create a `StateSaveLocation` directory
        # so we make one here that is only r/w by owner.
        Path("/var/lib/slurm/slurm.state").mkdir(mode=0o600, exist_ok=True)

        if self._service_name == "slurmd":
            override = Path("/etc/systemd/system/slurmd.service.d/10-slurmd-conf-server.conf")
            override.parent.mkdir(exist_ok=True, parents=True)
            override.write_text(
                textwrap.dedent(
                    """
                    [Service]
                    ExecStart=
                    ExecStart=/usr/bin/sh -c "/usr/sbin/slurmd -D -s $${SLURMD_CONFIG_SERVER:+--conf-server $$SLURMD_CONFIG_SERVER} $$SLURMD_OPTIONS"
                    """
                )
            )

    def version(self) -> str:
        """Get the current version of Slurm installed on the system."""
        try:
            return apt.DebianPackage.from_installed_package(self._service_name).version.number
        except apt.PackageNotFoundError as e:
            raise SlurmOpsError(f"unable to retrieve {self._service_name} version. reason: {e}")

    @property
    def etc_path(self) -> Path:
        """Get the path to the Slurm configuration directory."""
        return Path("/etc/slurm")

    @property
    def var_lib_path(self) -> Path:
        """Get the path to the Slurm variable state data directory."""
        return Path("/var/lib/slurm")

    def service_manager_for(self, type: _ServiceType) -> _ServiceManager:
        """Return the `ServiceManager` for the specified `ServiceType`."""
        return _SystemctlServiceManager(type)

    def _env_manager_for(self, type: _ServiceType) -> _EnvManager:
        """Return the `_EnvManager` for the specified `ServiceType`."""
        return _EnvManager(file=self._env_file, prefix=type.value)


class _JWTKeyManager:
    """Control the JWT key used by Slurm.

    Todo:
        Use `jwtctl` to provide backend for generating, setting, and getting
        JWT key used by `slurmctld` and `slurmrestd`. This way we won't need to
        pass the `snap` bool as an argument to `__init__`
    """

    def __init__(self, keyfile: Path) -> None:
        self._keyfile = keyfile

    def get(self) -> str:
        """Get the current jwt key."""
        return self._keyfile.read_text()

    def set(self, key: str) -> None:
        """Set a new jwt key."""
        self._keyfile.write_text(key)

    def generate(self) -> None:
        """Generate a new, cryptographically secure jwt key."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.set(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()
        )


class _MungeKeyManager:
    """Control the munge key via `mungectl ...` commands."""

    @staticmethod
    def get() -> str:
        """Get the current munge key.

        Returns:
            The current munge key as a base64-encoded string.
        """
        return _mungectl("key", "get")

    @staticmethod
    def set(key: str) -> None:
        """Set a new munge key.

        Args:
            key: A new, base64-encoded munge key.
        """
        _mungectl("key", "set", stdin=key)

    @staticmethod
    def generate() -> None:
        """Generate a new, cryptographically secure munge key."""
        _mungectl("key", "generate")


class _MungeManager:
    """Manage `munged` service operations."""

    def __init__(self, ops_manager: _OpsManager) -> None:
        self.service = ops_manager.service_manager_for(_ServiceType.MUNGED)
        self.key = _MungeKeyManager()


class _PrometheusExporterManager:
    """Manage `prometheus-slurm-exporter` service operations."""

    def __init__(self, ops_manager: _OpsManager) -> None:
        self.service = ops_manager.service_manager_for(_ServiceType.PROMETHEUS_EXPORTER)


class _SlurmManagerBase:
    """Base manager for Slurm services."""

    def __init__(self, service: _ServiceType, snap: bool = False) -> None:
        self._ops_manager = _SnapManager() if snap else _AptManager(service)
        self.service = self._ops_manager.service_manager_for(service)
        self.munge = _MungeManager(self._ops_manager)
        self.jwt = _JWTKeyManager(self._ops_manager.var_lib_path / "slurm.data/jwt_hs256.key")
        self.exporter = _PrometheusExporterManager(self._ops_manager)
        self.install = self._ops_manager.install
        self.version = self._ops_manager.version

    @property
    def hostname(self) -> str:
        """The hostname where this manager is running."""
        return socket.gethostname().split(".")[0]

    @staticmethod
    def scontrol(*args) -> str:
        """Control Slurm via `scontrol` commands.

        Raises:
            SlurmOpsError: Raised if scontrol command fails.
        """
        return _call("scontrol", *args).stdout


class SlurmctldManager(_SlurmManagerBase):
    """Manager for the Slurmctld service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=_ServiceType.SLURMCTLD, *args, **kwargs)
        self.config = _SlurmConfigManager(self._ops_manager.etc_path / "slurm.conf")
        self.cgroup = _CgroupConfigManager(self._ops_manager.etc_path / "cgroup.conf")


class SlurmdManager(_SlurmManagerBase):
    """Manager for the Slurmd service.

    This service will additionally provide some environment variables that need to be
    passed through to the service in case the default service is overriden (e.g. a systemctl file override).

        - SLURMD_CONFIG_SERVER. Sets the `--conf-server` option for `slurmd`.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=_ServiceType.SLURMD, *args, **kwargs)
        self._env_manager = self._ops_manager._env_manager_for(_ServiceType.SLURMD)

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


class SlurmdbdManager(_SlurmManagerBase):
    """Manager for the Slurmdbd service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=_ServiceType.SLURMDBD, *args, **kwargs)
        self.config = _SlurmdbdConfigManager(self._ops_manager.etc_path / "slurmdbd.conf")


class SlurmrestdManager(_SlurmManagerBase):
    """Manager for the Slurmrestd service."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(service=_ServiceType.SLURMRESTD, *args, **kwargs)
