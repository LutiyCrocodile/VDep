from __future__ import annotations

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.templating import Jinja2Templates


def get_templates() -> Jinja2Templates:
    env = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html", "xml"]),
        cache_size=0,
        auto_reload=True,
    )
    return Jinja2Templates(env=env)


templates = get_templates()
