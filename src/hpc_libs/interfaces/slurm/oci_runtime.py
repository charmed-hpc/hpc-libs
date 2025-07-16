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

"""Integration interface implementation for the `slurm_oci_runtime` interface."""

__all__ = [
    "OCIRuntimeData",
    "OCIRuntimeDisconnectedEvent",
    "OCIRuntimeReadyEvent",
    "OCIRuntimeProvider",
    "OCIRuntimeRequirer",
]

from dataclasses import dataclass

import ops
from slurmutils import OCIConfig

from hpc_libs.interfaces.slurm.common import (
    SlurmctldProvider,
    SlurmctldRequirer,
    encoder,
)
from hpc_libs.utils import leader


@dataclass
class OCIRuntimeData:
    """Data provided by the OCI runtime.

    Attributes:
        ociconfig: OCI runtime data in `oci.conf` configuration file format.
    """

    ociconfig: OCIConfig

    def __post_init__(self) -> None:  # noqa D105
        if isinstance(self.ociconfig, dict):  # `ociconfig` is not fully deserialized.
            object.__setattr__(self, "ociconfig", OCIConfig(self.ociconfig))


class OCIRuntimeReadyEvent(ops.RelationEvent):
    """Event emitted when the OCI runtime application leader is ready.

    Notes:
        The OCI runtime application leader is "ready" once it is installed on
        each principal unit and able to share its configuration information
        required by the Slurm controller `slurmctld`.
    """


class OCIRuntimeDisconnectedEvent(ops.RelationEvent):
    """Event emitted when the OCI runtime application is disconnected from `slurmctld`."""


class _OCIRunTimeRequirerEvents(ops.CharmEvents):
    """`slurm_oci_runtime` requirer events."""

    oci_runtime_ready = ops.EventSource(OCIRuntimeReadyEvent)
    oci_runtime_disconnected = ops.EventSource(OCIRuntimeDisconnectedEvent)


class OCIRuntimeProvider(SlurmctldRequirer):
    """Integration interface implementation for `slurm_oci_runtime` providers.

    Notes:
        This interface should be used on the OCI runtime application leader to
        provide OCI runtime information to the `slurmctld` application leader.
    """

    @leader
    def set_oci_runtime_data(
        self, data: OCIRuntimeData, /, integration_id: int | None = None
    ) -> None:
        """Set OCI runtime data in the `slurm_oci_runtime` application databag.

        Args:
            data: OCI runtime data to set on an integrations' application databag.
            integration_id:
                (Optional) ID of integration to update. If no integration ID is passed,
                all integrations will be updated.

        Warnings:
            Only the OCI runtime application leader can set OCI runtime configuration data.
        """
        integrations = self.charm.model.relations.get(self._integration_name)
        if not integrations:
            return

        if integration_id is not None:
            integrations = [
                integration for integration in integrations if integration.id == integration_id
            ]

        for integration in integrations:
            integration.save(data, self.app, encoder=encoder)


class OCIRuntimeRequirer(SlurmctldProvider):
    """Integration interface implementation for `slurm_oci_runtime` requirers.

    Notes:
        This interface should be used on the `slurmctld` application leader
        retrieve data from the OCI runtime provider and edit the `oci.conf`
        configuration file.
    """

    on = _OCIRunTimeRequirerEvents()  # type: ignore

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
        """Handle when data from the OCI runtime application leader is ready."""
        provider_app = event.relation.app

        if not event.relation.data.get(provider_app):
            return

        self.on.oci_runtime_ready.emit(event.relation)

    @leader
    def _on_relation_broken(self, event: OCIRuntimeDisconnectedEvent) -> None:
        self.on.oci_runtime_disconnected.emit(event.relation)

    def get_oci_runtime_data(
        self, /, integration: ops.Relation | None = None, integration_id: int | None = None
    ) -> OCIRuntimeData | None:
        """Get OCI runtime data from the `slurm_oci_runtime` application databag.

        Args:
            integration: Integration instance to pull OCI runtime configuration data from.
            integration_id: Integration ID to pull OCI runtime configuration data from.

        Raises:
            ops.TooManyRelatedAppsError:
                Raised if neither `integration` nor `integration_id` are passed as arguments,
                but require-side application is integrated with multiple OCI runtime applications.
        """
        if not integration:
            integration = self.charm.model.get_relation(self._integration_name, integration_id)

        if not integration:
            return None

        return integration.load(OCIRuntimeData, integration.app)
