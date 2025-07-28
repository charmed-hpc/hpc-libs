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

"""Unit tests for the `slurmrestd` integration interface implementation."""

import json
from collections import defaultdict

import ops
import pytest
from ops import testing
from slurmutils import SlurmConfig

from hpc_libs.interfaces import (
    ControllerData,
    SlurmctldReadyEvent,
    SlurmrestdConnectedEvent,
    SlurmrestdProvider,
    SlurmrestdRequirer,
    controller_not_ready,
    wait_when,
)
from hpc_libs.utils import refresh

SLURMRESTD_INTEGRATION_NAME = "slurmrestd"
EXAMPLE_AUTH_KEY = "xyz123=="
EXAMPLE_SLURM_CONFIG = SlurmConfig(
    clustername="charmed-hpc-abc_",
    slurmctldhost=["127.0.0.1", "127.0.1.1"],
)


class MockSlurmrestdProviderCharm(ops.CharmBase):
    """Mock `slurmrestd` provider charm."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.slurmctld = SlurmrestdProvider(self, SLURMRESTD_INTEGRATION_NAME)

        framework.observe(
            self.slurmctld.on.slurmctld_ready,
            self._on_slurmctld_ready,
        )

    @refresh(check=None)
    @wait_when(controller_not_ready)
    def _on_slurmctld_ready(self, event: SlurmctldReadyEvent) -> None:
        data = self.slurmctld.get_controller_data(integration_id=event.relation.id)
        # Assume `remote_app_data` contains `auth_key` and `slurmconfig`.
        assert data.auth_key == EXAMPLE_AUTH_KEY
        assert data.slurmconfig.dict() == EXAMPLE_SLURM_CONFIG.dict()


class MockSlurmrestdRequirerCharm(ops.CharmBase):
    """Mock `slurmrestd` requirer charm."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self.slurmrestd = SlurmrestdRequirer(self, SLURMRESTD_INTEGRATION_NAME)

        framework.observe(
            self.slurmrestd.on.slurmrestd_connected,
            self._on_slurmrestd_connected,
        )

    def _on_slurmrestd_connected(self, event: SlurmrestdConnectedEvent) -> None:
        self.slurmrestd.set_controller_data(
            ControllerData(
                auth_key=EXAMPLE_AUTH_KEY,
                slurmconfig=EXAMPLE_SLURM_CONFIG,
            ),
            integration_id=event.relation.id,
        )


@pytest.fixture(scope="function")
def provider_ctx() -> testing.Context[MockSlurmrestdProviderCharm]:
    return testing.Context(
        MockSlurmrestdProviderCharm,
        meta={
            "name": "slurmrestd-provider",
            "provides": {SLURMRESTD_INTEGRATION_NAME: {"interface": "slurmrestd"}},
        },
    )


@pytest.fixture(scope="function")
def requirer_ctx() -> testing.Context[MockSlurmrestdRequirerCharm]:
    return testing.Context(
        MockSlurmrestdRequirerCharm,
        meta={
            "name": "slurmrestd-requirer",
            "requires": {SLURMRESTD_INTEGRATION_NAME: {"interface": "slurmrestd"}},
        },
    )


@pytest.mark.parametrize(
    "leader",
    (
        pytest.param(True, id="leader"),
        pytest.param(False, id="not leader"),
    ),
)
class TestSlurmrestdInterface:
    """Unit tests for the `slurmrestd` integration interface implementation."""

    # Test provider-side of the `slurmrestd` interface.

    @pytest.mark.parametrize(
        "ready",
        (
            pytest.param(True, id="ready"),
            pytest.param(False, id="not ready"),
        ),
    )
    def test_provider_on_slurmctld_ready_event(self, provider_ctx, leader, ready) -> None:
        """Test that the `slurmrestd` provider waits for controller data."""
        auth_key_secret = testing.Secret(tracked_content={"key": EXAMPLE_AUTH_KEY})

        slurmrestd_integration_id = 1
        slurmrestd_integration = testing.Relation(
            endpoint=SLURMRESTD_INTEGRATION_NAME,
            interface="sackd",
            id=slurmrestd_integration_id,
            remote_app_name="slurmrestd-requirer",
            remote_app_data={
                "auth_key": '"***"',
                "auth_key_id": json.dumps(auth_key_secret.id),
                "slurmconfig": EXAMPLE_SLURM_CONFIG.json(),
            }
            if ready
            else {"auth_key": '"***"'},
        )

        state = provider_ctx.run(
            provider_ctx.on.relation_changed(slurmrestd_integration),
            testing.State(
                leader=leader,
                relations={slurmrestd_integration},
                secrets={auth_key_secret},
            ),
        )

        if ready:
            # Assert that `SlurmctldReadyEvent` was emitted only once.
            occurred = defaultdict(lambda: 0)
            for event in provider_ctx.emitted_events:
                occurred[type(event)] += 1

            assert occurred[SlurmctldReadyEvent] == 1

            # Assert that there are no deferred events.
            assert len(state.deferred) == 0

            # Assert that the unit is not waiting for controller data.
            assert state.unit_status != ops.WaitingStatus("Waiting for controller data")
        else:
            # Assert that the charm defers events if there's missing integration data.
            assert len(state.deferred) == 1
            assert state.unit_status == ops.WaitingStatus("Waiting for controller data")

    # Test requires-side of the `slurmrestd` interface.

    def test_requirer_on_slurmrestd_connected_event(self, requirer_ctx, leader) -> None:
        """Test that `slurmctld` sets required integration data for `slurmrestd` to function."""
        slurmrestd_integration_id = 1
        slurmrestd_integration = testing.Relation(
            endpoint=SLURMRESTD_INTEGRATION_NAME,
            interface="slurmrestd",
            id=slurmrestd_integration_id,
            remote_app_name="slurmrestd-provider",
        )

        state = requirer_ctx.run(
            requirer_ctx.on.relation_created(slurmrestd_integration),
            testing.State(leader=leader, relations={slurmrestd_integration}),
        )

        integration = state.get_relation(slurmrestd_integration_id)
        if leader:
            # Verify that the leader unit has set the required data for `sackd`.
            assert "auth_key" in integration.local_app_data
            assert integration.local_app_data["auth_key"] == '"***"'

            assert "auth_key_id" in integration.local_app_data
            assert integration.local_app_data["auth_key_id"] != '""'

            assert "slurmconfig" in integration.local_app_data
            assert integration.local_app_data["slurmconfig"] == EXAMPLE_SLURM_CONFIG.json()
        else:
            # Verify that non-leader units have not set anything in `local_app_data`.
            assert integration.local_app_data == {}
