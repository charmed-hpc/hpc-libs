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

"""Base classes, methods, and utilities for building HPC-related integration interfaces."""

__all__ = [
    "ConditionEvaluation",
    "Condition",
    "Secret",
    "Interface",
    "update_app_data",
    "integration_exists",
    "integration_not_exists",
    "block_when",
    "wait_when",
]

import json
import logging
from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any, Self

import ops

from hpc_libs.utils import StopCharm

_logger = logging.getLogger(__name__)

type ConditionEvaluation = tuple[bool, str]
type Condition = Callable[[ops.CharmBase], ConditionEvaluation]


class Secret:
    """Wrapper for interfacing with Juju secrets."""

    def __init__(self, secret: ops.Secret) -> None:
        self._secret = secret

    @property
    def uri(self) -> str:
        """Get the URI of this secret."""
        return self._secret.id or ""

    @classmethod
    def create_or_update(cls, charm: ops.CharmBase, label: str, content: dict[str, str]) -> Self:
        """Create or update a secret.

        Args:
            charm: Charm to associate secret with.
            label: Secret label.
            content: Payload to set as secret content.
        """
        try:
            secret = charm.model.get_secret(label=label)
            secret.set_content(content=content)
        except ops.SecretNotFoundError:
            secret = charm.app.add_secret(label=label, content=content)

        return cls(secret)

    @classmethod
    def load(cls, charm: ops.CharmBase, label: str) -> Self | None:
        """Load a secret.

        Args:
            charm: Charm to load secret from.
            label: Secret label.
        """
        try:
            secret = charm.model.get_secret(label=label)
            return cls(secret)
        except ops.SecretNotFoundError:
            return None

    def grant(self, relation: ops.Relation) -> None:
        """Grant read access to this secret.

        Args:
            relation: Integration to grant read access to.
        """
        self._secret.grant(relation)

    def remove(self) -> None:
        """Remove all revisions of this secret."""
        self._secret.remove_all_revisions()


class Interface(ops.Object):
    """Base interface for HPC-related integrations.

    Notes:
        This interface is not intended to be used directly. Child interfaces should inherit
        from this interface to provide common macros typically used within custom integration
        interface implementations.
    """

    def __init__(self, charm: ops.CharmBase, integration_name: str) -> None:
        super().__init__(charm, integration_name)
        self.charm = charm
        self.app = charm.app
        self.unit = charm.unit
        self._integration_name = integration_name

    @property
    def integrations(self) -> list[ops.Relation]:
        """Get list of integration instances associated with the configured integration name."""
        return [
            integration
            for integration in self.charm.model.relations[self._integration_name]
            if self._is_integration_active(integration)
        ]

    def get_integration(self, integration_id: int | None = None) -> ops.Relation | None:
        """Get integration instance.

        Args:
            integration_id:
                ID of integration instance to retrieve. Required if there are
                multiple integrations of the same name in Juju's database.
                For example, you must pass the integration ID if multiple
                `slurmd` partitions exist.
        """
        return self.charm.model.get_relation(self._integration_name, integration_id)

    def ready(self, integration_id: int | None = None) -> bool:
        """Check if an integration is ready.

        Args:
            integration_id:
                Check if this specific integration instance is ready. If an
                integration ID is not provided, all existing integrations will
                be checked to determine if they are ready.

        Raises:
            IndexError: Raised if the provided integration ID does not exist.

        Notes:
            - This method can be used to check if a provider answered with the requested
              data outside an event callback.
            - An integration is "ready" once it is exporting the necessary data requested
              by a requirer to proceed.
        """
        if integration_id is None:
            return (
                all(self._is_integration_ready(integration) for integration in self.integrations)
                if self.integrations
                else False
            )

        try:
            integration = [
                integration
                for integration in self.integrations
                if integration.id == integration_id
            ][0]
            return self._is_integration_ready(integration)
        except IndexError:
            raise IndexError(f"integration id {integration_id} does not exist")

    def joined(self) -> bool:
        """Check if the integration is joined.

        Warnings:
            - This method only checks if the integration is joined. It does not check if the
              necessary data is available in the integration application/unit databag.
        """
        return True if self.model.relations.get(self._integration_name) else False

    @staticmethod
    def _is_integration_active(integration: ops.Relation) -> bool:
        """Check if an integration is active by accessing contained data."""
        try:
            _ = repr(integration.data)
            return True
        except (RuntimeError, ops.ModelError):
            return False

    @staticmethod
    def _is_integration_ready(integration: ops.Relation) -> bool:
        """Check if an integration is ready.

        Notes:
            - This static method should be overridden by inheriting child classes if they
              have specific fields that must be populated in an integration databag to be
              considered ready.
        """
        return True


def update_app_data(
    app: ops.Application,
    integration: ops.Relation,
    data: Mapping[str, Any],
    *,
    json_encoder: type[json.JSONEncoder] | None = None,
) -> None:
    """Update an application's databag in an integration.

    Args:
        app: Application to update.
        integration: Integration holding application's databag.
        data: Content to update application databag with.
        json_encoder: Optional json encoder to use for encoding complex data types.

    Raises:
        ops.RelationDataError: Raised if non-leader unit attempts to update application data.
    """
    data = {k: json.dumps(v, cls=json_encoder) for k, v in data.items()}
    integration.data[app].update(data)


def integration_exists(name: str) -> Condition:
    """Check if an integration exists.

    Args:
        name: Name of integration to check existence of.
    """

    def wrapper(charm: ops.CharmBase) -> ConditionEvaluation:
        return bool(charm.model.relations[name]), ""

    return wrapper


def integration_not_exists(name: str) -> Condition:
    """Check if an integration does not exist.

    Args:
        name: Name of integration to check existence of.
    """

    def wrapper(charm: ops.CharmBase) -> ConditionEvaluation:
        not_exists = not bool(charm.model.relations[name])
        return not_exists, f"Waiting for integrations: [`{name}`]" if not_exists else ""

    return wrapper


def block_when(*conditions: Condition) -> Callable[..., Any]:
    """Evaluate blocking conditions.

    If a condition is `True`, set a `BlockedStatus` message.

    Args:
        *conditions: Conditions to evaluate.
    """

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(charm: ops.CharmBase, *args: ops.EventBase, **kwargs: Any) -> Any:
            event, *_ = args
            _logger.debug("handling event `%s` on %s", event, charm.unit.name)

            for condition in conditions:
                result, msg = condition(charm)
                if result:
                    event.defer()
                    raise StopCharm(ops.BlockedStatus(msg))

            return func(charm, *args, **kwargs)

        return wrapper

    return decorator


def wait_when(*conditions: Condition) -> Callable[..., Any]:
    """Evaluate awaitable conditions.

    If a condition is `True`, set a `WaitingStatus` message.

    Args:
        *conditions: Conditions to evaluate.
    """

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(charm: ops.CharmBase, *args: ops.EventBase, **kwargs: Any) -> Any:
            event, *_ = args
            _logger.debug("handling event `%s` on unit %s", event, charm.unit.name)

            for condition in conditions:
                result, msg = condition(charm)
                if result:
                    event.defer()
                    raise StopCharm(ops.WaitingStatus(msg))

            return func(charm, *args, **kwargs)

        return wrapper

    return decorator
