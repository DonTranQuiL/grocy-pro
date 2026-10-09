"""Grocy Pro bundles grocy-py, so another `grocy` module can't break it.

Regression for 3.0.0/3.0.1 on systems that still have the old Grocy integration
(domain `grocy`): it pins grocy-py 0.1.0, which owns the same top-level `grocy`
module. Home Assistant swapped the installed version between the two pins and
the first one imported stayed in memory, so Grocy Pro failed with "cannot
import name 'EntityType' from 'grocy'" or refused to set up.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
import types
from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.grocy_pro import vendor
from custom_components.grocy_pro.const import DOMAIN

COMPONENT = Path(__file__).parent.parent / "custom_components" / DOMAIN
MODULES = [
    "",
    ".config_flow",
    ".coordinator",
    ".services",
    ".todo",
    ".calendar",
    ".sensor",
    ".binary_sensor",
]


@pytest.fixture
def foreign_grocy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put an unrelated `grocy` package in memory, like grocy-py 0.1.0 loaded
    by the old integration."""
    old = types.ModuleType("grocy")
    old.__path__ = []  # a package without the names Grocy Pro used to import
    monkeypatch.setitem(sys.modules, "grocy", old)
    for name in list(sys.modules):
        if name.startswith("grocy."):
            monkeypatch.delitem(sys.modules, name)


def test_no_grocy_py_requirement() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text("utf-8"))
    assert not [r for r in manifest["requirements"] if r.startswith("grocy-py")]


def test_never_imports_top_level_grocy() -> None:
    pattern = re.compile(r"^\s*(from grocy[ .]|import grocy\b)", re.M)
    for path in COMPONENT.rglob("*.py"):
        assert not pattern.search(path.read_text("utf-8")), path


def test_vendored_version() -> None:
    from custom_components.grocy_pro.vendor.grocy import EntityType, Grocy  # noqa: F401

    assert vendor.GROCY_PY_VERSION == "1.3.0"
    assert (COMPONENT / "vendor" / "grocy" / "LICENSE").is_file()


def test_modules_import_next_to_foreign_grocy(monkeypatch, foreign_grocy) -> None:
    for name in list(sys.modules):
        if name.startswith("custom_components.grocy_pro"):
            monkeypatch.delitem(sys.modules, name)
    for module in MODULES:
        importlib.import_module(f"custom_components.grocy_pro{module}")


async def test_setup_and_actions_next_to_foreign_grocy(
    hass: HomeAssistant, setup_integration, grocy_server, foreign_grocy
) -> None:
    entry = await setup_integration()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.grocy_stock").state != "unavailable"
    await hass.services.async_call(
        DOMAIN, "complete_task", {"task_id": 1}, blocking=True
    )
    assert ("POST", "tasks/1/complete") in [call[:2] for call in grocy_server.calls]


async def test_flow_works_next_to_foreign_grocy(
    hass: HomeAssistant, foreign_grocy
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM


async def test_old_restart_repair_is_removed(
    hass: HomeAssistant, setup_integration
) -> None:
    """3.0.1 could leave a 'restart required' repair behind."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        "restart_required",
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="restart_required",
    )
    await setup_integration()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "restart_required") is None
