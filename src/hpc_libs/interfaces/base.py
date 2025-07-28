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
    "Interface",
    "update_secret",
    "load_secret",
    "integration_exists",
    "integration_not_exists",
    "block_when",
    "wait_when",
]

import logging
from collections.abc import Callable, Iterable
from functools import partial, wraps
from typing import Any, Literal

import ops

from hpc_libs.utils import StopCharm

_logger = logging.getLogger(__name__)

type ConditionEvaluation = tuple[bool, str]
type Condition = Callable[[ops.CharmBase], ConditionEvaluation]


def update_secret(charm: ops.CharmBase, label: str, content: dict[str, str]) -> ops.Secret:
    """Update a secret.

    Args:
        charm: Charm to associate secret with.
        label: Secret label.
        content: Payload to set as secret content.

    Notes:
        - The secret will be created if it does not exist.
    """
    try:
        secret = charm.model.get_secret(label=label)
        secret.set_content(content=content)
    except ops.SecretNotFoundError:
        secret = charm.app.add_secret(label=label, content=content)

    return secret


def load_secret(charm: ops.CharmBase, label: str) -> ops.Secret | None:
    """Load a secret.

    Args:
        charm: Charm to load secret from.
        label: Secret label.
    """
    try:
        return charm.model.get_secret(label=label)
    except ops.SecretNotFoundError:
        return None


class Interface(ops.Object):
    """Base interface for HPC-related integrations.

    Args:
        charm: Charm instance the integration belongs to.
        integration_name: Name of the integration.
        required_app_data: Required application data for the integration to be considered ready.

    Notes:
        - This interface is not intended to be used directly. Child interfaces should inherit
          from this interface to provide common macros typically used within custom integration
          interface implementations.
        - An integration is considered "ready" once it is exporting the necessary data for
          a requirer/provider to successfully process a `RelationChangedEvent`.
    """

    def __init__(
        self,
        charm: ops.CharmBase,
        /,
        integration_name: str,
        *,
        required_app_data: Iterable[str] | None = None,
    ) -> None:
        super().__init__(charm, integration_name)
        self.charm = charm
        self.app = charm.app
        self.unit = charm.unit
        self._integration_name = integration_name
        self._required_app_data = required_app_data if required_app_data else set()

    @property
    def integrations(self) -> list[ops.Relation]:
        """Get list of integration instances associated with the configured integration name."""
        return [
            integration
            for integration in self.charm.model.relations[self._integration_name]
            if self._is_integration_active(integration)
        ]

    def get_integration(self, integration_id: int | None = None) -> ops.Relation:
        """Get integration instance.

        Args:
            integration_id:
                ID of integration instance to retrieve. Required if there are
                multiple integrations of the same name in Juju's database.
                For example, you must pass the integration ID if multiple
                `slurmd` partitions exist.

        Raises:
            ops.RelationNotFoundError:
                Raised if integration is not established. If `integration_id` is set,
                raised if integration instance is not established or found.
            ops.TooManyRelatedAppsError:
                Raised if `integration_id` is not passed as an argument,
                but multiple applications is are integrated on the same endpoint.
        """
        integration = self.charm.model.get_relation(self._integration_name, integration_id)
        if not integration:
            raise ops.RelationNotFoundError()

        return integration

    def is_ready(self, integration_id: int | None = None) -> bool:
        """Check if an integration is ready.

        Args:
            integration_id:
                Check if this specific integration instance is ready. If an
                integration ID is not provided, all existing integrations will
                be checked to determine if they are ready.

        Raises:
            ops.RelationNotFoundError: Raised if the provided integration ID does not exist.

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

        if integration := self.get_integration(integration_id):
            return self._is_integration_ready(integration)
        else:
            raise ops.RelationNotFoundError()

    def is_joined(self) -> bool:
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

    def _is_integration_ready(self, integration: ops.Relation) -> bool:
        """Check if an integration is ready."""
        if not integration.app:
            return False

        return all(k in integration.data[integration.app] for k in self._required_app_data)

    def _load_integration_data[T](
        self,
        cls: type[T],
        /,
        integration: ops.Relation | None = None,
        integration_id: int | None = None,
        *,
        target: Literal["app", "unit"] = "app",
        decoder: Callable[[str], Any] | None = None,
    ) -> list[T]:
        """Load integration data.

        Args:
            cls: Dataclass that will wrap integration data.
            integration: Integration instance to pull data.
            integration_id: Integration ID to pull data from.
            target: Pull data from either the application or unit databag.
            decoder: Callable that will be used to decode each field.

        Returns:
            A `MutableSet` containing integration data. If `target` is set to `"app"`, the
            returned `MutableSet` will only contain one object holding the application data.
        """
        if not integration:
            integration = self.get_integration(integration_id)

        if target == "app":
            return [integration.load(cls, integration.app, decoder=decoder)]
        else:
            return [integration.load(cls, unit, decoder=decoder) for unit in integration.units]

    def _save_integration_data(
        self,
        data: object,
        /,
        target: ops.Application | ops.Unit,
        integration_id: int | None = None,
        *,
        encoder: Callable[[Any], str] | None = None,
    ) -> None:
        """Save integration data.

        Args:
            data: Dataclass object to save to the integration.
            target: Location to save object.
            integration_id: ID of integration to update.
            encoder: Callable that will be used to encode each field.
        """
        integrations = self.integrations
        if integration_id is not None:
            integrations = [self.get_integration(integration_id)]

        for integration in integrations:
            integration.save(data, target, encoder=encoder)


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


def _status_when(*conditions: Condition, status: type[ops.StatusBase]) -> Callable[..., Any]:
    """Evaluate conditions.

    If a condition is `True`, set a new status message.

    Args:
        *conditions: Conditions to evaluate.
        status: Status type to set if a condition is evaluated to be `True`.
    """

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(charm: ops.CharmBase, *args: ops.EventBase, **kwargs: Any) -> Any:
            event, *_ = args
            _logger.debug("handling event `%s` on %s", event, charm.unit.name)

            for condition in conditions:
                result, msg = condition(charm)
                if result:
                    _logger.debug(
                        (
                            "condition '%s' evaluated to be `True`. deferring event `%s` and "
                            + "updating status of unit %s to `%s` with message '%s'"
                        ),
                        condition.__name__,
                        event,
                        charm.unit.name,
                        status.__name__,
                        msg,
                    )
                    event.defer()
                    raise StopCharm(status(msg))

            return func(charm, *args, **kwargs)

        return wrapper

    return decorator


block_when = partial(_status_when, status=ops.BlockedStatus)
wait_when = partial(_status_when, status=ops.WaitingStatus)
