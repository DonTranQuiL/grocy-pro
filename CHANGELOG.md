# Changelog

## 3.0.1 (2026-10-09)

### Fixed

- *"Error occurred loading flow for integration grocy_pro: cannot import name
  'EntityType' from 'grocy'"*. The old Grocy integration loaded grocy-py 0.1.0
  (which owns the same `grocy` module). Home Assistant installs grocy-py 1.3.0
  for Grocy Pro on disk, but Python keeps 0.1.0 in memory until a restart.
  Grocy Pro now imports only from module paths that exist in both versions,
  checks which version is really loaded, and shows a **Restart Home
  Assistant** repair (and a clear message in the setup dialog) instead of
  failing.
- The *"Detected blocking call to import_module ... config_flow inside the
  event loop"* warning: Home Assistant retries a failed import in the event
  loop, so it went away with the import fix.

### Docs

- Upgrade steps and troubleshooting for the HACS download failing with the
  old `custom_components/grocy` path (restart Home Assistant before
  downloading; remove, restart and re-add if it already failed).

## 3.0.0 (2026-10-09)

Stable release of 3.0.0-beta.1 with no code changes. It had to become the
latest stable release: HACS takes the install folder from the latest stable
release, so while that was 2.0.0 (domain `grocy`), installing the beta failed
with *"No manifest.json file found 'custom_components/grocy/manifest.json'"*.
If you see that error, remove the repository from HACS, restart Home Assistant
and add it again.

A rewrite with its own domain. **Breaking:** read the upgrade steps in the
[README](README.md#upgrading-from-2x-the-grocy-domain).

### Renamed: `grocy` → `grocy_pro` ("Grocy Pro")

- The integration now lives in `custom_components/grocy_pro`. 2.x shared the
  folder and domain with the original custom-components/grocy integration,
  which HACS removed from its default list. HACS therefore kept reporting the
  installation as "removed by the owner".
- Actions moved from `grocy.*` to `grocy_pro.*`.
- Setup offers **Move my old Grocy setup**: it reuses the old URL and API key
  and removes the old entry, so entity IDs (`sensor.grocy_*`) and history are
  kept.
- The to-do list is now `todo.grocy_shopping_list` (was
  `todo.grocy_grocy_shopping_list`).

### New

- Calendar entity from Grocy's iCal feed (due products, chores, tasks,
  batteries, meal plan).
- The dashboard card ships with the integration and loads automatically, is
  listed in the card picker and has a visual editor. Options: `title`,
  `locations`, `entity_prefix`, `show_pictures`, `show_log`, `confirm_delete`.
- Repair issue when an old copy of the card (`/local/grocy-action-card.js`)
  is still loaded and would override the new one.
- Re-authentication when the API key is rejected, and Reconfigure to change the
  connection.
- Diagnostics download (API key and URL redacted).
- Dutch translation. All UI strings, actions and errors are translatable.
- `add_products_by_name` accepts a unique partial name match and reports the
  names it couldn't match.
- `remove_product_in_shopping_list` takes an `amount`.

### Improved

- Polls Grocy's `db-changed-time` every 30 s and only downloads data when
  something changed (at least every 5 minutes), instead of fetching everything
  every 30 s.
- One `/stock/volatile` request for expiring, overdue, expired and missing
  products. Overdue chores, tasks and batteries are derived locally.
- Updated to grocy-py 1.3.0 (Grocy 4.x data models). Requires Home Assistant
  2026.4 or newer.
- All Grocy requests have a 20 s timeout.
- Item lists are excluded from the recorder (only the counts are stored).
- Product pictures work again (grocy-py drops the picture name; it is now read
  from the raw product objects).

### Fixed

- A port typed into the URL was added a second time (`host:9192:9192`).
- Chores, batteries and the meal plan showed empty names and recipes.
- The picture proxy forwarded `Content-Encoding`/`Content-Length` from Grocy,
  corrupting compressed responses; it also registered twice on reload.
- Grocy errors in actions now show a readable message instead of a stack trace.
- Card, reviewed line by line:
  - "Nothing here ??": the empty-section emoji was mangled by a non-UTF-8
    copy. The source is now ASCII-only (`\u` escapes), enforced by a test.
  - Follows the Home Assistant theme (light and dark) instead of hard-coded
    colours, no longer downloads Google Fonts, and its styles live in a shadow
    root so they can't leak into the rest of the dashboard.
  - Re-rendered on every state change anywhere in Home Assistant; now only
    when one of its five entities changes. One click listener instead of new
    listeners per render.
  - Items you acted on stayed hidden until a page reload, so a recurring chore
    disappeared for good after "Done". They now come back with fresh data.
  - All Grocy text (names, notes, picture URLs, location names, title) is
    HTML-escaped.
  - Errors show the reason in the log and the button can be used again.
  - Missing entities (or a wrong `entity_prefix`) and an unreachable Grocy show
    a notice instead of "all clear".
  - The bin icon deletes the task or chore in Grocy; it now asks first.
  - Dates are read as local calendar days (no off-by-one), Grocy's "never"
    date shows "No due date", and chores/tasks say "due" instead of "expires".
  - Removing a shopping list item crashed (undefined variable) and ignored the
    amount; amounts are no longer rounded to whole numbers; a second copy of
    the card no longer throws "already defined".
  - One column on narrow cards (container query, also in Sections), buttons
    wrap on phones; visual editor and Sections grid size.
  - The card URL carries a content hash, so browsers load every new version.
- Manifest: documentation and issue tracker pointed at the old repository;
  codeowner typo.

### Removed

- `json_encoder.py` (no longer needed).
- The `/local/grocy-action-card.js` installation step.

## 2.x

Fork of custom-components/grocy with the Grocy Command Center card. See the
[GitHub releases](https://github.com/DonTranQuiL/grocy-pro/releases).
