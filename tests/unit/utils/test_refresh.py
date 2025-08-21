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

"""Unit tests for the `refresh` utility."""

import ops
import pytest
from ops import testing

from hpc_libs.utils import StopCharm, refresh

refresh_no_check_func = refresh()
refresh = refresh(hook=lambda _: ops.ActiveStatus())


class MockCharm(ops.CharmBase):
    """Mock charm for testing the `refresh` decorator."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.stop, self._on_stop)

    @refresh
    def _on_install(self, _: ops.InstallEvent) -> None:
        if not self.unit.is_leader():
            raise StopCharm(ops.BlockedStatus("more than 1 unit not supported"))

    @refresh_no_check_func
    def _on_stop(self, _: ops.StopEvent) -> None: ...


@pytest.fixture(scope="function")
def mock_charm_ctx() -> testing.Context[MockCharm]:
    return testing.Context(
        MockCharm,
        meta={
            "name": "mock-refresh-charm",
        },
    )


@pytest.mark.parametrize("leader", (True, False))
def test_refresh(mock_charm_ctx, leader) -> None:
    """Test that `refresh` correctly updates a unit's status."""
    state = mock_charm_ctx.run(mock_charm_ctx.on.install(), testing.State(leader=leader))

    if leader:
        assert state.unit_status == ops.ActiveStatus()
    else:
        assert state.unit_status == ops.BlockedStatus("more than 1 unit not supported")


def test_refresh_no_check_func(mock_charm_ctx) -> None:
    """Test that `refresh` does not change a unit's state if no `check` function is provided."""
    state = mock_charm_ctx.run(mock_charm_ctx.on.stop(), testing.State())
    assert state.unit_status == ops.UnknownStatus()
