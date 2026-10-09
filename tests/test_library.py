"""An old grocy-py (from the 2.x `grocy` integration) must not break Grocy Pro.

Regression for "cannot import name 'EntityType' from 'grocy'": grocy-py 0.1.0
was still loaded in memory after Home Assistant installed 1.3.0 on disk.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import grocy
import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.grocy_pro import library
from custom_components.grocy_pro.const import DOMAIN

MANIFEST = Path(__file__).parent.parent / "custom_components" / DOMAIN / "manifest.json"
COMPONENT = MANIFEST.parent


@pytest.fixture
def old_grocy_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate grocy-py 0.1.0 in memory: no EntityType at the package root."""
    monkeypatch.delattr(grocy, "EntityType")


def test_required_version_matches_manifest() -> None:
    requirements = json.loads(MANIFEST.read_text("utf-8"))["requirements"]
    assert f"grocy-py=={library.REQUIRED_GROCY_PY}" in requirements


def test_no_problem_with_current_library() -> None:
    assert library.library_problem() is None


def test_problem_when_old_version_loaded(old_grocy_loaded) -> None:
    assert library.library_problem() == {
        "installed": library.REQUIRED_GROCY_PY,
        "loaded": "an older version (0.x)",
        "required": library.REQUIRED_GROCY_PY,
    }


def test_problem_when_old_version_installed(monkeypatch) -> None:
    monkeypatch.setattr(library, "installed_grocy_py", lambda: "0.1.0")
    assert library.library_problem()["installed"] == "0.1.0"


def test_only_stable_submodule_imports() -> None:
    """Import names from submodules that exist in grocy-py 0.1.0 and 1.x,
    so the integration always imports and can show the restart message."""
    for path in COMPONENT.glob("*.py"):
        for line in path.read_text("utf-8").splitlines():
            assert not line.strip().startswith("from grocy import "), (path.name, line)


def test_modules_import_with_old_library(monkeypatch, old_grocy_loaded) -> None:
    """With 0.1.0 in memory the integration still imports, so Home Assistant
    neither fails the flow nor falls back to importing it in the event loop
    ("Detected blocking call to import_module ... config_flow")."""
    for name in list(sys.modules):
        if name.startswith("custom_components.grocy_pro"):
            monkeypatch.delitem(sys.modules, name)
    for module in (
        "__init__",
        "config_flow",
        "services",
        "todo",
        "calendar",
        "sensor",
        "binary_sensor",
    ):
        name = "custom_components.grocy_pro" + (
            "" if module == "__init__" else f".{module}"
        )
        importlib.import_module(name)


async def test_entry_not_ready_and_repair(
    hass: HomeAssistant, mock_entry, grocy_server, frozen, old_grocy_loaded
) -> None:
    mock_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "restart_required")
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.ERROR
    assert issue.translation_placeholders["required"] == library.REQUIRED_GROCY_PY


async def test_flow_aborts_with_restart_message(
    hass: HomeAssistant, old_grocy_loaded
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "restart_required"


async def test_issue_cleared_when_fixed(hass: HomeAssistant, setup_integration) -> None:
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
