# Copyright 2026 Canonical Ltd.
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

"""Unit tests for secret utilities."""

import ops
import pytest
from ops import testing

from charmed_hpc_libs.ops import load_secret, update_secret


class MockCharm(ops.CharmBase):
    """Mock charm for testing secret utilities."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        framework.observe(self.on.load_secret_action, self._load_secret)
        framework.observe(self.on.update_secret_action, self._update_secret)

    def _load_secret(self, _: ops.ActionEvent) -> None:
        # Load a secret that exists.
        secret = load_secret(self, "test-secret")
        assert secret.get_content()["key"] == "supersecret"

        # Attempt to load a secret that does not exist.
        secret = load_secret(self, "nonexistent-secret")
        assert secret is None

    def _update_secret(self, _: ops.ActionEvent) -> None:
        # Update a secret that exists.
        update_secret(self, "test-secret", content={"key": "newsupersecret"})

        # Update a secret that does not exist.
        update_secret(self, "new-secret", content={"key": "yowzah"})


@pytest.fixture(scope="function")
def mock_charm() -> testing.Context[MockCharm]:
    return testing.Context(
        MockCharm,
        meta={"name": "mock-secrets-charm"},
        actions={
            "load-secret": {},
            "update-secret": {"params": {"value": {"type": "string"}}},
        },
    )


def test_load_secret(mock_charm) -> None:
    """Test the `load_secret` function."""
    secret = testing.Secret(label="test-secret", tracked_content={"key": "supersecret"})

    mock_charm.run(mock_charm.on.action("load-secret"), state=testing.State(secrets={secret}))


def test_update_secret(mock_charm) -> None:
    """Test the `update_secret` function."""
    secret = testing.Secret(
        label="test-secret", tracked_content={"key": "supersecret"}, owner="app"
    )

    state = mock_charm.run(
        mock_charm.on.action("update-secret"), state=testing.State(secrets={secret}, leader=True)
    )

    secret = state.get_secret(label="test-secret")
    assert secret.latest_content["key"] == "newsupersecret"
    secret = state.get_secret(label="new-secret")
    assert secret.latest_content["key"] == "yowzah"
