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

"""Unit tests for the `systemd` machine library."""

import subprocess
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from hpc_libs.errors import SystemdError
from hpc_libs.machine import SystemctlServiceManager, systemctl


def test_systemctl(mocker: MockerFixture) -> None:
    """Test the `systemctl` function."""
    mock_run = mocker.patch.object(subprocess, "run")
    mock_run.side_effect = subprocess.CalledProcessError(
        cmd=["systemctl", "start", "slurmctld"],
        returncode=1,
        output="",
        stderr="failed to start slurmctld service",
    )

    # Test `systemctl` function with check set to `False`,
    stdout, exit_code = systemctl("start", "slurmctld", check=False)
    assert stdout is None
    assert exit_code == 1

    # Test `systemctl` function with check set to `True`.
    with pytest.raises(SystemdError) as exec_info:
        systemctl("start", "slurmctld", check=True)

    assert exec_info.type == SystemdError
    assert exec_info.value.message == (
        "systemctl command 'systemctl start slurmctld' failed with exit code 1. "
        + "reason: failed to start slurmctld service"
    )


class TestSystemctlServiceManager:
    """Test the `SystemctlServiceManager` class."""

    @pytest.fixture
    def service_manager(self) -> SystemctlServiceManager:
        """Create a `SystemctlServiceManager` object."""
        return SystemctlServiceManager("slurmctld")

    @pytest.fixture
    def mock_systemctl(self, mocker: MockerFixture) -> Mock:
        """Create a mocked `systemctl` function."""
        return mocker.patch("hpc_libs.machine.systemd.systemctl")

    def test_start(self, service_manager, mock_systemctl) -> None:
        """Test the `start` method."""
        service_manager.start()
        mock_systemctl.assert_called_with("start", "slurmctld")

    def test_stop(self, service_manager, mock_systemctl) -> None:
        """Test the `stop` method."""
        service_manager.stop()
        mock_systemctl.assert_called_with("stop", "slurmctld")

    def test_enable(self, service_manager, mock_systemctl) -> None:
        """Test the `enable` method."""
        service_manager.enable()
        mock_systemctl.assert_called_with("enable", "slurmctld")

    def test_disable(self, service_manager, mock_systemctl) -> None:
        """Test the `disable` method."""
        service_manager.disable()
        mock_systemctl.assert_called_with("disable", "slurmctld")

    def test_restart(self, service_manager, mock_systemctl) -> None:
        """Test the `restart` method."""
        service_manager.restart()
        mock_systemctl.assert_called_with("restart", "slurmctld")

    @pytest.mark.parametrize(
        "mock_result,expected",
        (
            pytest.param(("", 0), True, id="active"),
            pytest.param(("", 1), False, id="not active"),
        ),
    )
    def test_is_active(self, service_manager, mock_systemctl, mock_result, expected) -> None:
        """Test the `active` method."""
        mock_systemctl.return_value = mock_result
        assert service_manager.is_active() is expected
        mock_systemctl.assert_called_with("is-active", "--quiet", "slurmctld", check=False)
