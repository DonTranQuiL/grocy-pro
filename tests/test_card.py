"""Run the dashboard card in headless Chrome against real entity states.

Skipped when no Chrome/Chromium is installed (GitHub's Ubuntu runners have one).
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant

from custom_components.grocy_pro.const import DOMAIN

ROOT = Path(__file__).parent.parent
CARD = ROOT / "custom_components" / DOMAIN / "frontend" / "grocy-action-card.js"
HARNESS = Path(__file__).parent / "card" / "harness.js"
ENTITIES = [
    "sensor.grocy_stock",
    "sensor.grocy_shopping_list",
    "sensor.grocy_chores",
    "sensor.grocy_tasks",
    "binary_sensor.grocy_overdue_batteries",
]
CHROME = next(
    (
        shutil.which(name)
        for name in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        )
        if shutil.which(name)
    ),
    None,
)


def test_card_source_is_ascii() -> None:
    """Non-ASCII must be \\u-escaped so a wrong charset can't mangle it ('??')."""
    source = CARD.read_bytes()
    bad = [i for i, byte in enumerate(source) if byte > 127]
    assert not bad, f"non-ASCII byte at offset {bad[0]}"


def test_card_calls_only_existing_services() -> None:
    """Every service the card calls exists, with fields that exist."""
    services = yaml.safe_load((CARD.parent.parent / "services.yaml").read_text("utf-8"))
    source = CARD.read_text("utf-8")
    calls = re.findall(r'\["(\w+)", \{([^}]*)\}', source)
    assert len(calls) >= 7
    for service, body in calls:
        assert service in services, service
        keys = set(re.findall(r"(\w+):", body))
        assert keys <= set(services[service]["fields"]), (service, keys)


def _run_chrome(page: Path) -> dict:
    out = subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--window-size=1200,900",
            "--virtual-time-budget=5000",
            "--dump-dom",
            page.as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    ).stdout
    match = re.search(r'<pre id="out">(.*?)</pre>', out, re.S)
    assert match, out[-2000:]
    return json.loads(html.unescape(match.group(1)))


@pytest.mark.skipif(CHROME is None, reason="no Chrome/Chromium installed")
async def test_card_in_browser(
    hass: HomeAssistant, setup_integration, grocy_server
) -> None:
    """Render, click every action, and check escaping, notices and layout."""
    await setup_integration()
    states = {}
    for entity_id in ENTITIES:
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        states[entity_id] = json.loads(json.dumps(state.as_dict(), default=str))
    # The demo list only has a note; add a product line so "Remove" is covered.
    states["sensor.grocy_shopping_list"]["attributes"]["products"].append(
        {
            "id": 99,
            "product_id": 2,
            "amount": 2.0,
            "note": "the big one",
            "product": {"id": 2, "name": "Chocolate"},
            "done": False,
        }
    )

    page_html = (
        "<!doctype html><html><head><meta charset='utf-8'></head><body>"
        f"<script type='application/json' id='states'>{json.dumps(states).replace('</', '<\\/')}</script>"
        "<pre id='out'></pre>"
        f"<script type='module'>{CARD.read_text('utf-8')}\n{HARNESS.read_text('utf-8')}</script>"
        "</body></html>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "card.html"
        page.write_text(page_html, "utf-8")
        result = await hass.async_add_executor_job(_run_chrome, page)

    checks = result["checks"]
    assert result["errors"] == []
    assert checks["items"] > 10
    assert checks["bad_text"] == []
    assert "Shopping list" in checks["sections"]
    assert checks["pictures"] >= 1
    assert checks["wide_columns"] == 2
    assert checks["renders_on_same_states"] == 0
    assert checks["renders_on_unrelated_change"] == 0
    assert set(checks["clicked"]) >= {
        "consume",
        "waste",
        "open_product",
        "complete_task",
        "execute_chore",
        "track_battery",
        "remove_shopping",
    }
    # open_product doesn't hide; the other actions do
    assert checks["hidden_after_actions"] == len(checks["clicked"]) - 1
    assert checks["delete_cancel_calls"] == 0
    assert checks["clicked_delete"] is True
    assert checks["items_after_refresh"] == checks["items"]
    assert "failed (boom <b>bold</b>)" in checks["error_logged"]
    assert checks["error_has_markup"] == 0
    assert checks["button_enabled_after_error"] is True
    assert checks["timers_after_disconnect"] == 0
    assert checks["xss_img"] == 0
    assert checks["xss_text"] is True
    assert checks["xss_fired"] == 0
    assert checks["missing_notice"] is True
    assert checks["unavailable_notice"] is True
    assert checks["narrow_columns"] == 1
    assert checks["narrow_overflow"] is False
    assert checks["bad_config"] == "rejected"
    assert checks["stub"] == {}
    assert checks["editor_fields"] == [
        "title",
        "entity_prefix",
        "show_pictures",
        "show_log",
        "confirm_delete",
    ]
    assert checks["editor_config"] == {
        "type": "custom:grocy-action-card",
        "title": "Kitchen",
        "show_log": False,
    }

    # Every payload the card sent is accepted by the real action schemas and
    # reaches Grocy.
    assert all(call["domain"] == DOMAIN for call in result["calls"])
    for call in result["calls"]:
        await hass.services.async_call(
            DOMAIN, call["service"], call["data"], blocking=True
        )
