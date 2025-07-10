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

"""Integration interface implementation for the `slurmd` interface."""

__all__ = [
    "ComputeData",
    "SlurmdReadyEvent",
    "SlurmdDisconnectedEvent",
    "SlurmdProvider",
    "SlurmdRequirer",
    "partition_not_ready",
]

from dataclasses import asdict, dataclass
from typing import Any

import ops
from slurmutils import Partition

from hpc_libs.interfaces.base import ConditionEvaluation, update_app_data
from hpc_libs.interfaces.slurm.common import SlurmctldProvider, SlurmctldRequirer, SlurmJSONEncoder
from hpc_libs.utils import leader


@dataclass(frozen=True)
class ComputeData:
    """Data provided by the Slurm compute service, `slurmd`."""

    partition: Partition


def partition_not_ready(charm: ops.CharmBase) -> ConditionEvaluation:
    """Check if compute - `slurmd` - data is available.

    Notes:
        - This condition check requires that the charm has a public `slurmd`
          attribute that has a public `ready` method.
    """
    not_ready = not charm.slurmd.ready()  # type: ignore
    return not_ready, "Waiting for partition data" if not_ready else ""


class SlurmdReadyEvent(ops.RelationEvent):
    """Event emitted the primary `slurmd` unit is ready.

    Notes:
        The `slurmd` application is ready once the leader unit is fully initialized
        and able to share the partition configuration information required by the
        Slurm controller, `slurmctld`.
    """


class SlurmdDisconnectedEvent(ops.RelationEvent):
    """Event emitted when the `slurmd` applications is disconnected from `slurmctld`."""


class _SlurmdRequirerEvents(ops.ObjectEvents):
    """`slurmd` requirer events."""

    slurmd_ready = ops.EventSource(SlurmdReadyEvent)
    slurmd_disconnected = ops.EventSource(SlurmdDisconnectedEvent)


class SlurmdProvider(SlurmctldRequirer):
    """Integration interface implementation for `slurmd` service providers.

    This interface should be used on `slurmd` units to retrieve controller data
    from the `slurmctld` application leader.
    """

    @leader
    def set_compute_data(self, data: ComputeData, /, integration_id: int | None = None) -> None:
        """Set compute data in the `slurmd` application databag.

        Args:
            data: Compute data to set on an integrations' application databag.
            integration_id:
                (Optional) ID of integration to update. If no integration ID is passed,
                all integrations will be updated.

        Warnings:
            Only the `slurmd` application leader can set compute configuration data.
        """
        integrations = self.charm.model.relations.get(self._integration_name)
        if not integrations:
            return

        if integration_id is not None:
            integrations = [
                integration for integration in integrations if integration.id == integration_id
            ]

        for integration in integrations:
            update_app_data(self.app, integration, asdict(data), json_encoder=SlurmJSONEncoder)


class SlurmdRequirer(SlurmctldProvider):
    """Integration interface implementation for `slurmd` service requirers.

    This interface should be used on the `slurmctld` application leader to
    enlist new `slurmd` partitions, and managed the partition configuration.
    """

    on = _SlurmdRequirerEvents()  # type: ignore

    def __init__(self, charm: ops.CharmBase, integration_name: str) -> None:
        super().__init__(charm, integration_name)

        self.framework.observe(
            self.charm.on[self._integration_name].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self.charm.on[self._integration_name].relation_broken,
            self._on_relation_broken,
        )

    @leader
    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Handle when data from the `slurmd` application leader is ready."""
        if not event.relation.data.get(event.relation.app):
            return

        self.on.slurmd_ready.emit(event.relation)

    @leader
    def _on_relation_broken(self, event: ops.RelationBrokenEvent) -> None:
        """Handle when a `slurmd` application is disconnected from the controller, `slurmctld`."""
        super()._on_relation_broken(event)
        self.on.slurmd_disconnected.emit(event.relation)

    def get_compute_data(
        self, /, integration: ops.Relation | None = None, integration_id: int | None = None
    ) -> ComputeData | None:
        """Get compute data from the `slurmd` application databag.

        Args:
            integration: Integration instance to pull compute data from.
            integration_id: Integration ID to pull compute data from.

        Raises:
            ops.TooManyRelatedAppsError:
                Raised if neither `integration` nor `integration_id` are passed as arguments,
                but require-side application is integrated with multiple `slurmd` applications.
        """
        if not integration:
            integration = self.get_integration(integration_id)

        if not integration:
            return None

        provider_app_data: dict[str, Any] = dict(integration.data.get(integration.app))  # type: ignore
        if config := provider_app_data.get("partition"):
            provider_app_data["partition"] = Partition.from_json(config)

        return ComputeData(**provider_app_data) if provider_app_data else None

    @staticmethod
    def _is_integration_ready(integration: ops.Relation) -> bool:
        """Check if the `partition` field has been populated."""
        if not integration.app:
            return False

        return "partition" in integration.data[integration.app]
