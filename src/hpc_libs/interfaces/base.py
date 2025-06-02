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

__all__ = ["BaseInterface", "update_app_data"]

import json
from collections.abc import Mapping
from typing import Any

import ops

INTEGRATION_CONTENT_KEY = "data"


class BaseInterface(ops.Object):
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

    @staticmethod
    def _is_integration_active(integration: ops.Relation) -> bool:
        """Check if an integration is active by accessing contained data."""
        try:
            _ = repr(integration.data)
            return True
        except (RuntimeError, ops.ModelError):
            return False


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
