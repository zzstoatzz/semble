from typing import Any


def drop_none(**kwargs: Any) -> dict[str, Any]:
    """build a params/body dict, omitting unset values.

    keys are passed in api casing (camelCase) directly.
    """
    return {k: v for k, v in kwargs.items() if v is not None}
