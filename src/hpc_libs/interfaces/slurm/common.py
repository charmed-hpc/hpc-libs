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

"""Common classes, methods, and utilities shared between Slurm-related integration interfaces."""

__all__ = [
    "ControllerData",
    "SlurmctldConnectedEvent",
    "SlurmctldReadyEvent",
    "SlurmctldDisconnectedEvent",
    "SlurmctldProvider",
    "SlurmctldRequirer",
    "controller_not_ready",
    "encoder",
]

import json
from dataclasses import dataclass
from string import Template
from typing import Any

import ops
from slurmutils import Model

from hpc_libs.interfaces.base import (
    ConditionEvaluation,
    Interface,
    load_secret,
    update_secret,
)
from hpc_libs.utils import leader

AUTH_KEY_TEMPLATE_LABEL = Template("integration-$id-auth-key-secret")


def encoder(value: Any) -> str:
    """Encode Slurm integration data."""
    if isinstance(value, Model):
        value = value.dict()

    return json.dumps(value)


@dataclass(frozen=True)
class ControllerData:
    """Data provided by the Slurm controller service, `slurmctld`.

    Attributes:
        auth_key: Base64-encoded string representing the `auth/slurm` key.
        controllers:
            List of controller addresses for that can be used by Slurm services
            for contacting the `slurmctld` application. The first entry in the list is the
            primary `slurmctld` service. Other entries are failovers.
        auth_key_id: ID of the `auth/slurm` key Juju secret for this integration instance.
    """

    auth_key: str
    controllers: list[str]
    auth_key_id: str | None = None


def controller_not_ready(charm: ops.CharmBase) -> ConditionEvaluation:
    """Check if controller - `slurmctld` - data is available.

    Notes:
        - This condition check requires that the charm has a public `slurmctld`
          attribute that has a public `ready` method.
    """
    not_ready = not charm.slurmctld.ready()  # type: ignore
    return not_ready, "Waiting for controller data" if not_ready else ""


class SlurmctldConnectedEvent(ops.RelationEvent):
    """Event emitted when `slurmctld` is connected to a Slurm-related application."""


class SlurmctldReadyEvent(ops.RelationEvent):
    """Event emitted when the primary `slurmctld` service is ready.

    Notes:
        The `slurmctld` application is ready once it is fully initialized and able to share
        the configuration information required by other Slurm services such as `slurmd`.
    """


class SlurmctldDisconnectedEvent(ops.RelationEvent):
    """Event emitted when `slurmctld` is disconnected from a Slurm-related application."""


class _SlurmctldRequirerEvents(ops.CharmEvents):
    """`slurmctld` requirer events."""

    slurmctld_connected = ops.EventSource(SlurmctldConnectedEvent)
    slurmctld_ready = ops.EventSource(SlurmctldReadyEvent)
    slurmctld_disconnected = ops.EventSource(SlurmctldDisconnectedEvent)


class SlurmctldProvider(Interface):
    """Base interface for `slurmctld` providers to consume Slurm service data.

    Notes:
        This interface is not intended to be used directly. Child interfaces should inherit
        from this interface so that they can provide `slurmctld` data and consume configuration
        provide by other Slurm services such as `slurmd` or `slurmdbd`.
    """

    def __init__(self, charm: ops.CharmBase, integration_name: str) -> None:
        super().__init__(charm, integration_name)

        self.framework.observe(
            self.charm.on[self._integration_name].relation_broken,
            self._on_relation_broken,
        )

    @leader
    def _on_relation_broken(self, event: ops.RelationBrokenEvent) -> None:
        """Revoke the departing application's access to Slurm secrets."""
        if auth_secret := load_secret(
            self.charm,
            label=AUTH_KEY_TEMPLATE_LABEL.substitute(id=event.relation.id),
        ):
            auth_secret.remove_all_revisions()

    @leader
    def set_controller_data(
        self, content: ControllerData, /, integration_id: int | None = None
    ) -> None:
        """Set `slurmctld` controller data for Slurm services on application databag.

        Args:
            content: `slurmctld` provider data to set on application databag.
            integration_id:
                Grant an integration access to Slurm secrets. This argument must not
                be set to the ID of an integration if that integration requires
                access to Slurm secrets.
        """
        integrations = self.charm.model.relations.get(self._integration_name)
        if not integrations:
            return

        if integration_id is not None:
            if integration := self.get_integration(integration_id):
                secret = update_secret(
                    self.charm,
                    AUTH_KEY_TEMPLATE_LABEL.substitute(id=integration_id),
                    {"key": content.auth_key},
                )
                secret.grant(integration)
                object.__setattr__(content, "auth_key_id", secret.id)

                integrations = [integration]
            else:
                raise IndexError(f"integration id {integration_id} does not exist")

        # Redact secrets. "***" indicates that an interface did not unlock a secret.
        object.__setattr__(content, "auth_key", "***")

        for integration in integrations:
            integration.save(content, self.app, encoder=encoder)


class SlurmctldRequirer(Interface):
    """Base interface for applications to retrieve data provided by `slurmctld`.

    Notes:
        This interface is not intended to be used directly. Child interfaces should inherit
        from this is interface to consume data from the Slurm controller `slurmctld` and provide
        necessary configuration information to `slurmctld`.
    """

    on = _SlurmctldRequirerEvents()  # type: ignore

    def __init__(self, charm: ops.CharmBase, integration_name: str) -> None:
        super().__init__(charm, integration_name)

        self.framework.observe(
            self.charm.on[self._integration_name].relation_created,
            self._on_relation_created,
        )
        self.framework.observe(
            self.charm.on[self._integration_name].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self.charm.on[self._integration_name].relation_broken,
            self._on_relation_broken,
        )

    def _on_relation_created(self, event: ops.RelationCreatedEvent) -> None:
        """Handle when `slurmctld` is connected to an application."""
        self.on.slurmctld_connected.emit(event.relation)

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Handle when data from the primary `slurmctld` unit is ready."""
        if not event.relation.data.get(event.app):
            return

        self.on.slurmctld_ready.emit(event.relation)

    def _on_relation_broken(self, event: ops.RelationBrokenEvent) -> None:
        """Handle when `slurmctld` is disconnected from an application."""
        self.on.slurmctld_disconnected.emit(event.relation)

    def get_controller_data(
        self, integration: ops.Relation | None = None, integration_id: int | None = None
    ) -> ControllerData | None:
        """Get controller data from the `slurmctld` application databag."""
        if not integration:
            integration = self.get_integration(integration_id)

        if not integration:
            return None

        data = integration.load(ControllerData, integration.app)
        if data.auth_key_id:
            auth_key = self.charm.model.get_secret(id=data.auth_key_id)
            object.__setattr__(data, "auth_key", auth_key.get_content().get("key"))

        return data

    @staticmethod
    def _is_integration_ready(integration: ops.Relation) -> bool:
        """Check if the `auth_key_id` and `controllers` fields have been populated."""
        if not integration.app:
            return False

        return all(k in integration.data[integration.app] for k in ["auth_key_id", "controllers"])
