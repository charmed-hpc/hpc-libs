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

"""Integration interface implementation for the `slurmrestd` interface."""

__all__ = [
    "SlurmrestdConnectedEvent",
    "SlurmrestdProvider",
    "SlurmrestdRequirer",
]

import ops

from hpc_libs.interfaces.slurm.common import SlurmctldProvider, SlurmctldRequirer
from hpc_libs.utils import leader


class SlurmrestdConnectedEvent(ops.RelationEvent):
    """Event emitted when a new `slurmrestd` application is connected to `slurmctld`."""


class _SlurmrestdRequirerEvents(ops.ObjectEvents):
    """`slurmrestd` requirer events."""

    slurmrestd_connected = ops.EventSource(SlurmrestdConnectedEvent)


class SlurmrestdProvider(SlurmctldRequirer):
    """Integration interface implementation for `slurmrestd` service providers.

    This interface should be used on `slurmrestd` units to retrieve controller data
    from the `slurmctld` application leader.
    """

    @staticmethod
    def _is_integration_ready(integration: ops.Relation) -> bool:
        if not integration.app:
            return False

        return all(k in integration.data[integration.app] for k in ["auth_key_id", "slurmconfig"])


class SlurmrestdRequirer(SlurmctldProvider):
    """Integration interface implementation for `slurmrestd` service requirers.

    This interface should be used on the `slurmctld` application leader to provide
    Slurm controller data to `slurmrestd` units.
    """

    on = _SlurmrestdRequirerEvents()  # type: ignore

    def __init__(self, charm: ops.CharmBase, integration_name: str) -> None:
        super().__init__(charm, integration_name)

        self.framework.observe(
            self.charm.on[self._integration_name].relation_created,
            self._on_relation_created,
        )

    @leader
    def _on_relation_created(self, event: ops.RelationCreatedEvent) -> None:
        """Handle when a new `slurmrestd` application is connected to `slurmctld`."""
        self.on.slurmrestd_connected.emit(event.relation)
