"""Every schema this codebase asks a model to fill in must be one Gemini will accept.

These are checked structurally rather than by calling the API, because the rejection
happens at request time: a stubbed model in every other test will happily "return" a
shape the real provider refuses. That is exactly how an open-ended `dict` field reached
production in the recovery planner — 200-odd passing tests, and the first real call
failed at the node that had never been exercised for real.
"""

import pytest

from app.agents.recovery import _RecoveryPlan
from app.agents.risk import _RiskReport
from app.projects.service import _Answer

# Every model passed to llm.ask_for anywhere in the app.
SCHEMAS = [("_RiskReport", _RiskReport), ("_RecoveryPlan", _RecoveryPlan), ("_Answer", _Answer)]


def keys_in(node, key: str, path: str = "$") -> list[str]:
    """Every place `key` appears as a schema keyword — not inside a description."""
    found: list[str] = []
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                found.append(path)
            found += keys_in(value, key, f"{path}.{name}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += keys_in(value, key, f"{path}[{index}]")
    return found


@pytest.mark.parametrize("name,model", SCHEMAS, ids=[n for n, _ in SCHEMAS])
def test_no_open_ended_maps(name, model):
    """`dict[str, str]` on a model becomes an open-ended map, which the Gemini Developer
    API refuses outright: "only supported in Gemini Enterprise Agent Platform mode".
    Use a list of name/value pairs instead."""
    where = keys_in(model.model_json_schema(), "additionalProperties")

    assert not where, (
        f"{name} has an open-ended map at {where}. Gemini's Developer API rejects the "
        "whole request. Replace the dict field with a list of name/value pairs."
    )


@pytest.mark.parametrize("name,model", SCHEMAS, ids=[n for n, _ in SCHEMAS])
def test_every_field_is_typed(name, model):
    """A field with no type is a schema the provider cannot validate against."""
    schema = model.model_json_schema()
    untyped = [
        field
        for field, spec in (schema.get("properties") or {}).items()
        if not any(k in spec for k in ("type", "$ref", "anyOf", "allOf", "oneOf", "items"))
    ]

    assert not untyped, f"{name} has untyped field(s): {untyped}"


def test_the_guard_would_catch_a_regression():
    """If `keys_in` stopped finding anything, the tests above would pass vacuously."""
    from pydantic import BaseModel

    class Offender(BaseModel):
        params: dict[str, str] = {}

    assert keys_in(Offender.model_json_schema(), "additionalProperties")
