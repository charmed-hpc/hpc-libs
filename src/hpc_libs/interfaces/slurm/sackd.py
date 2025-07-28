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

"""Integration interface implementation for the `sackd` interface."""

__all__ = ["SackdConnectedEvent", "SackdProvider", "SackdRequirer"]

import ops

from hpc_libs.interfaces.slurm.common import SlurmctldProvider, SlurmctldRequirer
from hpc_libs.utils import leader


class SackdConnectedEvent(ops.RelationEvent):
    """Event emitted when a new `sackd` application is connected to `slurmctld`."""


class _SackdRequirerEvents(ops.ObjectEvents):
    """`sackd` requirer events."""

    sackd_connected = ops.EventSource(SackdConnectedEvent)


class SackdProvider(SlurmctldRequirer):
    """Integration interface implementation for `sackd` service providers.

    This interface should be used on `sackd` units to retrieve controller data
    from the `slurmctld` application leader.
    """

    def __init__(self, charm: ops.CharmBase, /, integration_name: str) -> None:
        super().__init__(charm, integration_name, required_app_data={"auth_key_id", "controllers"})


class SackdRequirer(SlurmctldProvider):
    """Integration interface implementation for `sackd` service requirers.

    This interface should be used on the `slurmctld` application leader to provide
    Slurm controller data to `sackd` units.
    """

    on = _SackdRequirerEvents()  # type: ignore

    def __init__(self, charm: ops.CharmBase, /, integration_name: str) -> None:
        super().__init__(charm, integration_name)

        self.framework.observe(
            self.charm.on[self._integration_name].relation_created,
            self._on_relation_created,
        )

    @leader
    def _on_relation_created(self, event: ops.RelationCreatedEvent) -> None:
        """Handle when a new `sackd` application is connected to `slurmctld`."""
        self.on.sackd_connected.emit(event.relation)
