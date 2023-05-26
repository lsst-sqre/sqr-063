"""Sphinx configuration.

To learn more about the Sphinx configuration for technotes, and how to
customize it, see:

https://documenteer.lsst.io/technotes/configuration.html
"""

from documenteer.conf.technote import *  # noqa: F401, F403

extensions.extend(["sphinxcontrib.redoc"])
redoc = [
    {
        "name": "Proof of concept REST API",
        "page": "poc-schema",
        "spec": "_static/poc-schema.json",
        "embed": True,
        "opts": {"hide-hostname": True},
    }
]
redoc_uri = (
    "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"
)
