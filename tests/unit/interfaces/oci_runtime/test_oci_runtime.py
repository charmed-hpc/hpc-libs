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

"""Unit tests for the `slurm_oci_runtime` integration interface implementation."""

from collections import defaultdict

import pytest
from mock_charms import (
    EXAMPLE_OCI_CONFIG,
    OCI_RUNTIME_INTEGRATION_NAME,
    MockOCIRunTimeProviderCharm,
    MockOCIRunTimeRequirerCharm,
)
from ops import testing
from slurmutils import OCIConfig

from hpc_libs.interfaces import OCIRunTimeDisconnectedEvent, OCIRunTimeReadyEvent


@pytest.fixture(scope="function")
def provider_ctx() -> testing.Context[MockOCIRunTimeProviderCharm]:
    return testing.Context(
        MockOCIRunTimeProviderCharm,
        meta={
            "name": "oci-runtime-provides",
            "provides": {OCI_RUNTIME_INTEGRATION_NAME: {"interface": "slurm_oci_runtime"}},
        },
    )


@pytest.fixture(scope="function")
def requirer_ctx() -> testing.Context[MockOCIRunTimeRequirerCharm]:
    return testing.Context(
        MockOCIRunTimeRequirerCharm,
        meta={
            "name": "oci-runtime-requires",
            "requires": {OCI_RUNTIME_INTEGRATION_NAME: {"interface": "slurm_oci_runtime"}},
        },
    )


@pytest.mark.parametrize("leader", (True, False))
def test_slurmctld_connected_event_handler(provider_ctx, leader) -> None:
    """Test that an OCI runtime provider correctly sets `oci.conf` data in application data."""
    oci_runtime_integration_id = 22
    oci_runtime_integration = testing.Relation(
        endpoint=OCI_RUNTIME_INTEGRATION_NAME,
        interface="oci-runtime",
        id=oci_runtime_integration_id,
        remote_app_name="slurmctld",
    )

    state = provider_ctx.run(
        provider_ctx.on.relation_created(oci_runtime_integration),
        testing.State(
            leader=leader,
            relations={oci_runtime_integration},
        ),
    )

    integration = state.get_relation(oci_runtime_integration_id)
    if leader:
        # Verify that the leader unit has set `oci.conf` data in `local_app_data`.
        assert "ociconfig" in integration.local_app_data
        config = OCIConfig.from_json(integration.local_app_data["ociconfig"])
        assert config.dict() == EXAMPLE_OCI_CONFIG.dict()
    else:
        # Verify that non-leader units have not set anything in `local_app_data`.
        assert integration.local_app_data == {}


@pytest.mark.parametrize("remote_app_data", ({}, {"ociconfig": EXAMPLE_OCI_CONFIG.json()}))
@pytest.mark.parametrize("leader", (True, False))
def test_oci_runtime_ready_event_handler(requirer_ctx, leader, remote_app_data) -> None:
    """Test that an OCI runtime requirer can consume `oci.conf` data from a runtime provider."""
    oci_runtime_integration_id = 22
    oci_runtime_integration = testing.Relation(
        endpoint=OCI_RUNTIME_INTEGRATION_NAME,
        interface="oci-runtime",
        id=oci_runtime_integration_id,
        remote_app_name="oci-runtime-provider",
        remote_app_data=remote_app_data,
    )

    requirer_ctx.run(
        requirer_ctx.on.relation_changed(oci_runtime_integration),
        testing.State(leader=leader, relations={oci_runtime_integration}),
    )

    if leader and remote_app_data:
        # `MockOCIRunTimeRequirerCharm` provides an assertion to check if `remote_app_data`
        #  can be read correctly to consume `oci.conf` data.

        # Assert that the last event emitted on the `leader` unit is an `OCIRunTimeReadyEvent`.
        assert isinstance(requirer_ctx.emitted_events[-1], OCIRunTimeReadyEvent)

        # Assert that `OCIRunTimeReadyEvent` was emitted only once.
        occurred = defaultdict(lambda: 0)
        for event in requirer_ctx.emitted_events:
            occurred[type(event)] += 1

        assert occurred[OCIRunTimeReadyEvent] == 1

    else:
        # Assert that `OCIRunTimeReadyEvent` is never emitted on non-leader units or on the
        # leader unit if `remote_app_data` is empty - e.g. blank `RelationChangedEvent` emitted
        # after `slurmctld` and `oci-runtime-provider` are integrated together.
        assert not any(
            isinstance(event, OCIRunTimeReadyEvent) for event in requirer_ctx.emitted_events
        )


@pytest.mark.parametrize("leader", (True, False))
def test_oci_runtime_disconnected_event_handler(requirer_ctx, leader) -> None:
    """Test that an OCI requirer properly captures when the runtime provider is disconnected."""
    oci_runtime_integration_id = 22
    oci_runtime_integration = testing.Relation(
        endpoint=OCI_RUNTIME_INTEGRATION_NAME,
        interface="oci-runtime",
        id=oci_runtime_integration_id,
        remote_app_name="oci-runtime-provider",
    )

    requirer_ctx.run(
        requirer_ctx.on.relation_broken(oci_runtime_integration),
        testing.State(leader=leader, relations={oci_runtime_integration}),
    )

    if leader:
        # Assert that the last event emitted on the `leader` unit is
        # an `OCIRunTimeDisconnectedEvent`.
        assert isinstance(requirer_ctx.emitted_events[-1], OCIRunTimeDisconnectedEvent)

        # Assert that `OCIRunTimeDisconnectedEvent` was emitted only once.
        occurred = defaultdict(lambda: 0)
        for event in requirer_ctx.emitted_events:
            occurred[type(event)] += 1

        assert occurred[OCIRunTimeDisconnectedEvent] == 1
    else:
        # Assert that `OCIRunTimeDisconnectEvent` is never emitted on non-leader units.
        assert not any(
            isinstance(event, OCIRunTimeDisconnectedEvent) for event in requirer_ctx.emitted_events
        )
