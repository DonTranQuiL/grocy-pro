#!/usr/bin/env python3
"""Daily check that the Grocy API still works with the grocy-py version Grocy Pro bundles.

Runs the same grocy-py calls the integration makes (see
custom_components/grocy_pro/grocy_data.py and calendar.py) against the public
demo at https://demo.grocy.info, which always runs the latest Grocy release.
A new Grocy release that grocy-py can no longer parse shows up here before users
report it.

Results are reduced to a stable fingerprint in .memory/grocy_api.json (Grocy
version plus, per check, the failing fields/error types). An issue is opened
only when a check newly fails. Network errors and 5xx count as transient. An
optional LLM (xAI first, then OpenRouter) adds a short impact summary.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests

# Use the grocy-py copy bundled with the integration (custom_components/
# grocy_pro/vendor/grocy), so the check runs exactly what users run.
VENDOR = Path(__file__).resolve().parent.parent / "custom_components" / "grocy_pro" / "vendor"
sys.path.insert(0, str(VENDOR))

COMPONENT = "custom_components/grocy_pro/"
DEMO_URL = "https://demo.grocy.info"
MEMORY_PATH = Path(".memory/grocy_api.json")
REPORT_PATH = Path("feed_watch_report.md")
TIMEOUT = 30


class Transient(Exception):
    """Network trouble that should not open an issue."""


def _install_timeout() -> None:
    """grocy-py has no timeouts; add one so a hanging demo can't stall the job."""
    from grocy import grocy_api_client

    real = grocy_api_client.requests

    class _Timeout:
        def __getattr__(self, name):
            attr = getattr(real, name)
            if name in ("get", "post", "put", "delete"):
                return lambda *a, **kw: attr(*a, **{"timeout": TIMEOUT, **kw})
            return attr

    grocy_api_client.requests = _Timeout()


def _describe(exc: Exception) -> list[str]:
    """Reduce an exception to stable strings (no dates or values)."""
    try:
        from pydantic import ValidationError
    except ImportError:  # pragma: no cover
        ValidationError = ()  # type: ignore[assignment]
    if isinstance(exc, ValidationError):
        return sorted(
            {
                f"{'.'.join(str(p) for p in err['loc'])}: {err['type']}"
                for err in exc.errors()
            }
        )
    status = getattr(exc, "status_code", None)
    if status is not None:
        return [f"{type(exc).__name__} HTTP {status}"]
    return [type(exc).__name__]


def _run(func):
    """Run a check; map network trouble to Transient."""
    from grocy.errors import GrocyError

    try:
        return func()
    except requests.RequestException as exc:
        raise Transient(type(exc).__name__) from exc
    except GrocyError as exc:
        if exc.status_code >= 500 or exc.status_code == 429:
            raise Transient(f"HTTP {exc.status_code}") from exc
        raise


def build_checks(api):
    from grocy import EntityType
    from grocy.data_models.product import Product

    def config():
        cfg = api.system.config()
        if cfg is None or not cfg.enabled_features:
            return ["system/config returned no enabled features"]
        return []

    def db_changed():
        if api.system.db_changed_time() is None:
            return ["system/db-changed-time returned nothing"]
        return []

    def stock():
        problems = []
        items = api.stock.current()
        if not items:
            problems.append("stock returned no products (demo should have stock)")
        raw = api.generic.list(EntityType.PRODUCTS) or []
        if raw and "picture_file_name" not in raw[0]:
            problems.append("objects/products no longer has picture_file_name")
        return problems

    def volatile():
        v = api.stock.volatile()
        for bucket in ("due_products", "overdue_products", "expired_products"):
            for item in getattr(v, bucket) or []:
                Product.from_stock_response(item)
        for item in v.missing_products or []:
            Product.from_missing_response(item)
        return []

    def shopping_list():
        api.shopping_list.items(get_details=True)
        return []

    def tasks():
        api.tasks.list()
        return []

    def chores():
        items = api.chores.list(get_details=True)
        if items and not all(c.name for c in items):
            return ["chores with get_details=True no longer include names"]
        return []

    def batteries():
        api.batteries.list(get_details=True)
        return []

    def meal_plan():
        api.meal_plan.items(
            get_details=True, query_filters=[f"day>={date.today().isoformat()}"]
        )
        return []

    def calendar():
        import icalendar

        text = api.calendar.ical()
        cal = icalendar.Calendar.from_ical(text or "")
        events = list(cal.walk("VEVENT"))
        if not events:
            return ["calendar/ical has no events (demo should have some)"]
        if any(e.get("DTSTART") is None for e in events):
            return ["calendar/ical has events without DTSTART"]
        return []

    return {
        "config": config,
        "db_changed_time": db_changed,
        "stock": stock,
        "volatile": volatile,
        "shopping_list": shopping_list,
        "tasks": tasks,
        "chores": chores,
        "batteries": batteries,
        "meal_plan": meal_plan,
        "calendar": calendar,
    }


def llm_summary(report: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return ""
    if os.getenv("XAI_API_KEY"):
        client, model = (
            OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ["XAI_API_KEY"]),
            "grok-4",
        )
    elif os.getenv("OPENROUTER_API_KEY"):
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        model = "deepseek/deepseek-v4.1-flash"
    else:
        return ""
    prompt = (
        "The Grocy API changed in a way the Home Assistant integration "
        f"{COMPONENT} (built on grocy-py) no longer handles. In at most 5 bullets, "
        "explain the user impact and whether a grocy-py upgrade or an "
        f"integration change is needed.\n\n{report}"
    )
    try:
        completion = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        print(f"LLM summary skipped: {exc}")
        return ""


def main() -> int:
    from grocy import Grocy

    _install_timeout()
    api = Grocy(DEMO_URL, "demo_mode", port=443)
    grocy_py = re.search(r'GROCY_PY_VERSION = "([^"]+)"', (VENDOR / "__init__.py").read_text()).group(1)

    previous: dict = {}
    if MEMORY_PATH.is_file():
        try:
            previous = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    prev_checks: dict[str, list[str]] = previous.get("checks", {})

    try:
        grocy_version = _run(lambda: api.system.info().grocy_version)
    except Transient as exc:
        print(f"Demo unreachable ({exc}); nothing to compare today.")
        return 0
    except Exception as exc:  # noqa: BLE001
        grocy_version = f"unknown ({type(exc).__name__})"
    print(f"Grocy {grocy_version}, grocy-py {grocy_py}")

    current: dict[str, list[str]] = {}
    fresh: dict[str, list[str]] = {}
    for name, check in build_checks(api).items():
        try:
            problems = _run(check)
        except Transient as exc:
            print(f"{name:16} transient ({exc}), keeping previous state")
            current[name] = prev_checks.get(name, [])
            continue
        except Exception as exc:  # noqa: BLE001
            problems = _describe(exc)
        current[name] = problems
        print(f"{name:16} {'ok' if not problems else 'PROBLEM: ' + '; '.join(problems)}")
        new = [p for p in problems if p not in prev_checks.get(name, [])]
        if new:
            fresh[name] = new

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(
        json.dumps(
            {"grocy_version": grocy_version, "grocy_py": grocy_py, "checks": current},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if not fresh:
        print("No breaking Grocy API changes.")
        return 0

    lines = [
        "## Grocy API change detected",
        "",
        f"The daily watcher ran the calls `{COMPONENT}` makes against {DEMO_URL} "
        f"(Grocy **{grocy_version}**, previously {previous.get('grocy_version', 'unknown')}) "
        f"with grocy-py **{grocy_py}** and found new failures:",
        "",
    ]
    for name, items in fresh.items():
        lines.append(f"### `{name}`")
        lines += [f"- {item}" for item in items]
        lines.append("")
    lines.append(
        "Check for a newer grocy-py release (https://pypi.org/project/grocy-py/) "
        "and copy it into custom_components/grocy_pro/vendor (see vendor/__init__.py)."
    )
    report = "\n".join(lines)
    summary = llm_summary(report)
    if summary:
        report += "\n\n### AI impact summary\n\n" + summary + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    env_file = os.getenv("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write("SCHEMA_CHANGED=true\n")
            fh.write(
                f"ISSUE_TITLE=Grocy API change ({grocy_version}): {', '.join(sorted(fresh))}\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
