#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""A placeholder charm for the HPC Libs."""

from ops import BlockedStatus
from ops.charm import CharmBase, StartEvent
from ops.main import main


class HPCLibsCharm(CharmBase):
    """Placeholder charm for HPC Libs."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.framework.observe(self.on.start, self._on_start)

    def _on_start(self, _: StartEvent) -> None:
        """Handle start event."""
        self.unit.status = BlockedStatus(
            "hpc-libs is not meant to be deployed as a standalone charm"
        )


if __name__ == "__main__":
    main(HPCLibsCharm)
