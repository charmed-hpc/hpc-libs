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

"""Unit tests for the `reconfigure` utility."""

import ops
import pytest
from ops import testing

from hpc_libs.utils import StopCharm, reconfigure, refresh


class MockCharm(ops.CharmBase):
    """Mock charm for testing the `reconfigure` decorator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.stop, self._on_stop)

    @refresh(hook=None)
    @reconfigure(hook=None)
    def _on_install(self, _: ops.InstallEvent) -> None:
        raise StopCharm(ops.BlockedStatus("no installation candidate"))

    @refresh(hook=None)
    @reconfigure(hook=None)
    def _on_start(self, _: ops.StartEvent) -> None:
        self.unit.status = ops.ActiveStatus()

    @reconfigure(hook=lambda _: None)
    def _on_stop(self, _: ops.StopEvent) -> None:
        self.unit.status = ops.MaintenanceStatus("stopping unit")


@pytest.fixture(scope="function")
def mock_charm() -> testing.Context[MockCharm]:
    return testing.Context(
        MockCharm,
        meta={
            "name": "mock-reconfigure-charm",
        },
    )


def test_reconfigure(mock_charm) -> None:
    state = mock_charm.run(mock_charm.on.install(), testing.State())
    assert state.unit_status == ops.BlockedStatus("no installation candidate")

    state = mock_charm.run(mock_charm.on.start(), testing.State())
    assert state.unit_status == ops.ActiveStatus()

    state = mock_charm.run(mock_charm.on.stop(), testing.State())
    assert state.unit_status == ops.MaintenanceStatus("stopping unit")
