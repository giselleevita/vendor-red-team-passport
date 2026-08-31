from __future__ import annotations

import json

from jinja2 import Environment, PackageLoader, select_autoescape


def template_environment() -> Environment:
    """Load bundled HTML templates in source, wheel, and zip-safe installations."""
    environment = Environment(
        loader=PackageLoader("apps.api", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    environment.filters["tojson"] = lambda obj, indent=2: json.dumps(obj, indent=indent)  # type: ignore[assignment]
    return environment
