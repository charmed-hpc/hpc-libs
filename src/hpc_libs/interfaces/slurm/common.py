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
    "SlurmctldConnectedEvent",
    "SlurmctldDisconnectedEvent",
    "SlurmJSONEncoder",
    "SlurmctldProvider",
    "SlurmctldRequirer",
]

import json
from typing import Any

import ops
from slurmutils import Model

from ..base import BaseInterface


class SlurmJSONEncoder(json.JSONEncoder):
    """Generic JSON encoder for Slurm-related integration data."""

    def default(self, o: Any) -> Any:  # noqa D102
        # Serialize Slurm configuration object if it is present.
        if isinstance(o, Model):
            return o.dict()

        return super().default(o)


class SlurmctldConnectedEvent(ops.RelationEvent):
    """Event emitted when `slurmctld` is connected to a Slurm-related application."""


class SlurmctldDisconnectedEvent(ops.RelationEvent):
    """Event emitted when `slurmctld` is disconnected from a Slurm-related application."""


class _SlurmctldRequirerEvents(ops.CharmEvents):
    """`slurmctld` requirer events."""

    slurmctld_connected = ops.EventSource(SlurmctldConnectedEvent)
    slurmctld_disconnected = ops.EventSource(SlurmctldDisconnectedEvent)


class SlurmctldProvider(BaseInterface):
    """Base interface for `slurmctld` providers to consume Slurm service data.

    Notes:
        This interface is not intended to be used directly. Child interfaces should inherit
        from this interface so that they can provide `slurmctld` data and consume configuration
        provide by other Slurm services such as `slurmd` or `slurmdbd`.
    """


class SlurmctldRequirer(BaseInterface):
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
            self.charm.on[self._integration_name].relation_broken,
            self._on_relation_broken,
        )

    def _on_relation_created(self, event: ops.RelationCreatedEvent) -> None:
        """Handle when `slurmctld` is connected to an application."""
        self.on.slurmctld_connected.emit(event.relation)

    def _on_relation_broken(self, event: ops.RelationBrokenEvent) -> None:
        """Handle when `slurmctld` is disconnected from an application."""
        self.on.slurmctld_disconnected.emit(event.relation)
