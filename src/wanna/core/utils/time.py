from datetime import datetime
from typing import Any, Dict

import pendulum
from jinja2 import Environment

_jinja_env = Environment()
_jinja_env.globals.update(modules={"pendulum": pendulum})


def get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def update_time_template(params: Dict[str, Any]):
    for k, v in params.items():
        if isinstance(v, str):
            v = _jinja_env.from_string(v).render()
        params[k] = v

    return params
