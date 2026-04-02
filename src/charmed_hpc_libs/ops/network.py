# Copyright 2026 Canonical Ltd.
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

"""Networking utilities."""

__all__ = ["get_ingress_address"]

import logging

import ops

from ..errors import IngressAddressNotFoundError

_logger = logging.getLogger(__name__)


def get_ingress_address(charm: ops.CharmBase, /, integration_name: str) -> str:
    """Get the ingress address of an integration endpoint.

    Args:
        charm: Charm integration endpoint is associated with.
        integration_name: Name of integration to look up network binding for.

    Raises:
        IngressAddressNotFoundError:
            Raised if the integration does not have a network binding.
        ops.RelationNotFoundError:
            Raised if the integration does not exist.
    """
    _logger.debug(
        "looking up network binding for integration '%s' in model `%s`",
        integration_name,
        charm.model.name,
    )

    if (binding := charm.model.get_binding(integration_name)) is not None:
        ingress_address = f"{binding.network.ingress_address}"
        _logger.debug(
            "ingress address for integration '%s' determined to be '%s'",
            integration_name,
            ingress_address,
        )
        return ingress_address

    _logger.error(
        "networking binding for integration '%s' in model `%s` does not exist",
        integration_name,
        charm.model.name,
    )
    raise IngressAddressNotFoundError(
        f"ingress address for integration '{integration_name}' was not found"
    )
