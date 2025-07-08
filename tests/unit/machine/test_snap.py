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

"""Unit tests for the `snap` machine library."""

import subprocess
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from hpc_libs.errors import SnapError
from hpc_libs.machine import SnapServiceManager, snap

# This input is modified. If the service name is the same as the snap name, then the
# service will be started as `snap start slurm` rather than `snap start slurm.slurm`.
# See https://snapcraft.io/prometheus for an example.
SNAP_INFO = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
commands:
    - slurm.command1
    - slurm.command2
services:
    slurmctld:                       simple, disabled, inactive
    slurm.logrotate:                 oneshot, enabled, inactive
    slurm.slurm-prometheus-exporter: simple, disabled, inactive
    slurm.slurmctld:                 simple, disabled, active
    slurm.slurmd:                    simple, enabled, active
    slurm.slurmdbd:                  simple, disabled, active
    slurm.slurmrestd:                simple, disabled, active
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
installed:          23.11.7             (x1) 114MB classic
"""

SNAP_INFO_NOT_INSTALLED = """
name:      slurm
summary:   "Slurm: A Highly Scalable Workload Manager"
publisher: –
store-url: https://snapcraft.io/slurm
license:   Apache-2.0
description: |
    Slurm is an open source, fault-tolerant, and highly scalable cluster
    management and job scheduling system for large and small Linux clusters.
channels:
    latest/stable:    –
    latest/candidate: 23.11.7 2024-06-26 (460) 114MB classic
    latest/beta:      ↑
    latest/edge:      23.11.7 2024-06-26 (459) 114MB classic
"""


def test_snap(mocker: MockerFixture) -> None:
    """Test the `snap` function."""
    mock_run = mocker.patch.object(subprocess, "run")
    mock_run.side_effect = subprocess.CalledProcessError(
        cmd=["snap", "start", "slurm.slurmctld"],
        returncode=1,
        output="",
        stderr="failed to start slurmctld service",
    )

    # Test `snap` function with check set to `False`.
    stdout, exit_code = snap("start", "slurm.slurmctld", check=False)
    assert stdout is None
    assert exit_code == 1

    # Test `snap` function with check set to `True`.
    with pytest.raises(SnapError) as exec_info:
        snap("start", "slurm.slurmctld", check=True)

    assert exec_info.type == SnapError
    assert exec_info.value.message == (
        "snap command 'snap start slurm.slurmctld' failed with exit code 1. "
        + "reason: failed to start slurmctld service"
    )


@pytest.mark.parametrize(
    "service_name_is_snap_name",
    (
        pytest.param(True, id="service name = snap name"),
        pytest.param(False, id="service name != snap name"),
    )
)
class TestSnapServiceManager:
    """Test the `SnapServiceManager` class."""

    @pytest.fixture
    def service_manager(self, service_name_is_snap_name) -> SnapServiceManager:
        """Create a `SnapServiceManager` object."""
        return SnapServiceManager(
            "slurmctld", snap="slurm" if not service_name_is_snap_name else None
        )

    @pytest.fixture
    def mock_snap(self, mocker: MockerFixture) -> Mock:
        """Create a mocked `snap` function."""
        return mocker.patch("hpc_libs.machine.snap.snap")

    def test_start(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `start` method."""
        service_manager.start()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("start", "slurmctld")
        else:
            mock_snap.assert_called_with("start", "slurm.slurmctld")

    def test_stop(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `stop` method."""
        service_manager.stop()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("stop", "slurmctld")
        else:
            mock_snap.assert_called_with("stop", "slurm.slurmctld")

    def test_enable(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `enable` method."""
        service_manager.enable()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("start", "--enable", "slurmctld")
        else:
            mock_snap.assert_called_with("start", "--enable", "slurm.slurmctld")

    def test_disable(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `disable` method."""
        service_manager.disable()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("stop", "--disable", "slurmctld")
        else:
            mock_snap.assert_called_with("stop", "--disable", "slurm.slurmctld")

    def test_restart(self, service_manager, mock_snap, service_name_is_snap_name) -> None:
        """Test the `restart` method."""
        service_manager.restart()
        if service_name_is_snap_name:
            mock_snap.assert_called_with("restart", "slurmctld")
        else:
            mock_snap.assert_called_with("restart", "slurm.slurmctld")

    @pytest.mark.parametrize(
        "mock_result,installed",
        (
            pytest.param((SNAP_INFO, 0), True, id="installed"),
            pytest.param((SNAP_INFO_NOT_INSTALLED, 1), False, id="not installed")
        )
    )
    def test_is_active(
        self,
        service_manager,
        mock_snap,
        mock_result,
        installed,
        service_name_is_snap_name,
    ) -> None:
        """Test the `active` method."""
        mock_snap.return_value = mock_result
        if installed:
            status = service_manager.is_active()
            if service_name_is_snap_name:
                mock_snap.assert_called_with("info", "slurmctld")
                assert status is False
            else:
                mock_snap.assert_called_with("info", "slurm")
                assert status is True
        else:
            with pytest.raises(SnapError) as exec_info:
                service_manager.is_active()

            assert exec_info.type == SnapError
            if service_name_is_snap_name:
                assert exec_info.value.message == (
                    "cannot retrieve 'slurmctld' service info with 'snap info slurmctld'"
                )
            else:
                assert exec_info.value.message == (
                    "cannot retrieve 'slurm.slurmctld' service info with 'snap info slurm'"
                )
