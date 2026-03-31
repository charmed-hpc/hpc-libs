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

"""Juju secret utilities."""

__all__ = ["load_secret", "update_secret"]

import ops


def load_secret(charm: ops.CharmBase, label: str) -> ops.Secret | None:
    """Load a secret.

    Args:
        charm: Charm to load secret from.
        label: Secret label.
    """
    try:
        return charm.model.get_secret(label=label)
    except (ops.ModelError, ops.SecretNotFoundError):
        return None


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
    except (ops.ModelError, ops.SecretNotFoundError):
        secret = charm.app.add_secret(label=label, content=content)

    return secret
