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
    "update_app_data",
    "integration_exists",
    "integration_not_exists",
    "block_when",
    "wait_when",
]

import json
import logging
from collections.abc import Callable, Mapping
from functools import partial, wraps
from typing import Any

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

        if integration := self.get_integration(integration_id):
            return self._is_integration_ready(integration)
        else:
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
