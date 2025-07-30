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

"""Unit tests for the `get_ingress_address` utility."""

from unittest.mock import Mock

import ops
import pytest
from ops import testing

from hpc_libs.errors import IngressAddressNotFoundError
from hpc_libs.utils import get_ingress_address

TEST_INTEGRATION_NAME = "test"
INTEGRATION_ADDRESS = None  # Global variable to check if the correct ingress address was pulled.


class MockCharm(ops.CharmBase):
    """Mock charm for testing the `get_ingress_address` utility function."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        framework.observe(self.on.update_status, self._on_update_status)

    def _on_update_status(self, _: ops.UpdateStatusEvent) -> None:
        global INTEGRATION_ADDRESS
        INTEGRATION_ADDRESS = get_ingress_address(self, TEST_INTEGRATION_NAME)

        # Assert an `IngressAddressNotFoundError` is emitted for non-existent integrations.
        with pytest.raises(ops.RelationNotFoundError):
            get_ingress_address(self, "yowzah")

        # Assert an `IngressAddressNotFoundError` is emitted if there is no networking binding.
        # Simulate a network error where integrations have no bindings.
        self.model.get_binding = Mock(return_value=None)
        with pytest.raises(IngressAddressNotFoundError):
            get_ingress_address(self, TEST_INTEGRATION_NAME)


@pytest.fixture(scope="function")
def mock_charm() -> testing.Context[MockCharm]:
    return testing.Context(
        MockCharm,
        meta={
            "name": "mock-get-ingress-address-charm",
            "requires": {TEST_INTEGRATION_NAME: {"interface": "test"}},
        },
    )


def test_get_ingress_address(mock_charm) -> None:
    """Test that `get_ingress_address` can successfully pull ingress addresses."""
    test_integration_id = 1
    test_integration = testing.Relation(
        endpoint=TEST_INTEGRATION_NAME,
        interface="test",
        id=test_integration_id,
        remote_app_name="test-integration-provider",
    )

    state = testing.State(relations={test_integration})
    ctx = mock_charm.run(mock_charm.on.update_status(), state)

    integration = ctx.get_relation(test_integration_id)
    assert INTEGRATION_ADDRESS == integration.local_unit_data["ingress-address"]
