/*
 * Grocy Pro Command Center card (custom:grocy-action-card).
 *
 * Served and registered by the Grocy Pro integration; no dashboard resource is
 * needed. Keep this file ASCII-only: non-ASCII characters are written as \u
 * escapes so a wrong charset can never mangle them.
 */

const CARD_TAG = "grocy-action-card";
const EDITOR_TAG = "grocy-action-card-editor";

const DEFAULTS = {
  title: "Grocy Pro",
  domain: "grocy_pro",
  entity_prefix: "grocy",
  show_pictures: true,
  show_log: true,
  confirm_delete: true,
};

const DEFAULT_LOCATIONS = { 1: "Pantry", 2: "Fridge", 3: "Freezer", 4: "Cupboards" };

// Entities the card reads: [platform, key, attribute holding the list].
const SOURCES = {
  stock: ["sensor", "stock", "products"],
  shopping: ["sensor", "shopping_list", "products"],
  chores: ["sensor", "chores", "chores"],
  tasks: ["sensor", "tasks", "tasks"],
  batteries: ["binary_sensor", "overdue_batteries", "overdue_batteries"],
};

const OPTIMISTIC_MAX_MS = 120000; // never hide a handled item longer than this
const OPTIMISTIC_MIN_MS = 2000; // ignore data updates that raced the action
const LOG_LINES = 6;
const DAY_MS = 86400000;

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" };

export function esc(value) {
  return String(value ?? "").replace(/[&<>"'`]/g, (c) => ESCAPES[c]);
}

/** Parse a Grocy date or naive datetime as local time. */
export function parseDate(value) {
  if (!value) return null;
  const text = String(value);
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(text);
  if (m && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(text.slice(10))) {
    return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0));
  }
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Whole calendar days from today to `value` (negative = past), or null. */
export function daysUntil(value, now = new Date()) {
  const date = parseDate(value);
  if (!date) return null;
  if (date.getFullYear() >= 2999) return Infinity; // Grocy's "never"
  const a = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const b = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((a - b) / DAY_MS);
}

export function dueText(value, now = new Date()) {
  const days = daysUntil(value, now);
  if (days === null) return "";
  if (days === Infinity) return "No due date";
  if (days < -1) return `${-days} days overdue`;
  if (days === -1) return "1 day overdue";
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}

function formatAmount(amount) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "";
  return String(Math.round(n * 100) / 100);
}

function shortUnit(name) {
  if (!name) return "";
  const unit = String(name).toLowerCase();
  if (unit === "l" || unit.includes("liter") || unit.includes("litre")) return "L";
  if (unit === "kg" || unit.includes("kilogram")) return "kg";
  if (unit === "g" || unit.includes("gram")) return "g";
  if (unit === "ml" || unit.includes("millilit")) return "ml";
  return ""; // pieces, packs, ...: just the number
}

const STYLE = `
  :host {
    --gp-bg: var(--ha-card-background, var(--card-background-color, #1c1c1c));
    --gp-text: var(--primary-text-color, #e1e1e1);
    --gp-muted: var(--secondary-text-color, #9b9b9b);
    --gp-border: var(--divider-color, rgba(127, 127, 127, 0.25));
    --gp-accent: var(--primary-color, #03a9f4);
    --gp-red: var(--error-color, #db4437);
    --gp-amber: var(--warning-color, #ffa600);
    --gp-green: var(--success-color, #43a047);
    --gp-tint: color-mix(in srgb, var(--gp-text) 4%, transparent);
    display: block;
  }
  ha-card { overflow: hidden; color: var(--gp-text); }
  .wrap { container-type: inline-size; }
  .header {
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
    gap: 12px; padding: 16px; border-bottom: 1px solid var(--gp-border);
  }
  .title { display: flex; align-items: center; gap: 10px; font-size: 1.15rem; font-weight: 700; min-width: 0; }
  .title ha-icon { color: var(--gp-accent); flex-shrink: 0; }
  .title span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .badges { display: flex; flex-wrap: wrap; gap: 8px; }
  .badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
    border-radius: 999px; font-size: 0.75rem; font-weight: 600;
    border: 1px solid var(--gp-border); background: var(--gp-tint);
  }
  .badge .dot { width: 8px; height: 8px; border-radius: 50%; }
  .badge.red .dot { background: var(--gp-red); }
  .badge.green .dot { background: var(--gp-green); }
  .notice {
    margin: 12px 16px 0; padding: 10px 12px; border-radius: 10px; font-size: 0.85rem;
    border: 1px solid color-mix(in srgb, var(--gp-amber) 50%, transparent);
    background: color-mix(in srgb, var(--gp-amber) 12%, transparent);
  }
  .notice code { font-size: 0.8rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px; }
  .column { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
  .section-label {
    display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--gp-muted);
  }
  .section-label ha-icon { --mdc-icon-size: 18px; }
  .section-label .count { margin-left: auto; font-weight: 600; letter-spacing: 0; }
  .items { display: flex; flex-direction: column; gap: 8px; }
  .item {
    display: flex; align-items: center; gap: 12px; padding: 10px 12px;
    border: 1px solid var(--gp-border); border-radius: 12px; background: var(--gp-tint);
  }
  .item.overdue { border-color: color-mix(in srgb, var(--gp-red) 55%, transparent); }
  .item.expiring { border-color: color-mix(in srgb, var(--gp-amber) 55%, transparent); }
  .lead {
    min-width: 40px; height: 40px; padding: 0 4px; box-sizing: border-box; flex-shrink: 0; border-radius: 8px; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--gp-border); font-size: 0.8rem; font-weight: 700; color: var(--gp-muted);
  }
  .lead img { width: 40px; height: 40px; margin: 0 -4px; object-fit: cover; }
  .lead ha-icon { --mdc-icon-size: 22px; color: var(--gp-accent); }
  .details { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .name { font-weight: 600; font-size: 0.9rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .meta { font-size: 0.75rem; color: var(--gp-muted); margin-top: 2px; }
  .meta.overdue { color: var(--gp-red); font-weight: 600; }
  .meta.expiring { color: var(--gp-amber); }
  .actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px; }
  button {
    font: inherit; font-size: 0.75rem; font-weight: 600; cursor: pointer;
    padding: 6px 12px; border-radius: 8px; min-height: 32px;
    color: var(--gp-accent); background: transparent;
    border: 1px solid color-mix(in srgb, var(--gp-accent) 55%, transparent);
  }
  button:hover:not(:disabled) { background: color-mix(in srgb, var(--gp-accent) 15%, transparent); }
  button:focus-visible { outline: 2px solid var(--gp-accent); outline-offset: 2px; }
  button.green { color: var(--gp-green); border-color: color-mix(in srgb, var(--gp-green) 55%, transparent); }
  button.red { color: var(--gp-red); border-color: color-mix(in srgb, var(--gp-red) 55%, transparent); }
  button.amber { color: var(--gp-amber); border-color: color-mix(in srgb, var(--gp-amber) 55%, transparent); }
  button.icon { padding: 4px; min-width: 32px; border-color: transparent; color: var(--gp-muted); }
  button.icon:hover:not(:disabled) { color: var(--gp-red); }
  button.icon ha-icon { --mdc-icon-size: 18px; }
  button:disabled { opacity: 0.5; cursor: progress; }
  .empty {
    padding: 14px; text-align: center; font-size: 0.8rem; color: var(--gp-muted);
    border: 1px dashed var(--gp-border); border-radius: 12px;
  }
  .log {
    border-top: 1px solid var(--gp-border); padding: 10px 16px; font-family: var(--code-font-family, monospace);
    font-size: 0.72rem; color: var(--gp-muted); max-height: 110px; overflow-y: auto;
  }
  .log .ok { color: var(--gp-green); }
  .log .err { color: var(--gp-red); }
  @container (max-width: 640px) {
    .grid { grid-template-columns: 1fr; }
  }
  @container (max-width: 400px) {
    .item { flex-wrap: wrap; }
    .details { flex-basis: calc(100% - 56px); }
    .actions { width: 100%; }
  }
`;

class GrocyActionCard extends HTMLElement {
  constructor() {
    super();
    this._config = { ...DEFAULTS };
    this._handled = new Map(); // "type:id" -> time the action succeeded
    this._busy = new Set(); // "type:id" of actions in flight
    this._log = [];
    this._signature = null;
    this._timers = new Set();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="wrap"></div></ha-card>`;
    this._root = this.shadowRoot.querySelector(".wrap");
    // One delegated listener for every button, so re-rendering never piles
    // up listeners.
    this._root.addEventListener("click", (ev) => this._onClick(ev));
  }

  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    if (config && typeof config !== "object") throw new Error("Invalid configuration");
    if (config && config.locations && typeof config.locations !== "object") {
      throw new Error("locations must be a map of Grocy location ID to name");
    }
    this._config = { ...DEFAULTS, ...(config || {}) };
    this._signature = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const signature = this._sourceStates().map((s) => s || null);
    const changed =
      !this._signature || signature.some((state, i) => state !== this._signature[i]);
    if (!changed) return; // nothing the card shows has changed
    if (this._signature) this._pruneHandled(true);
    this._signature = signature;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  disconnectedCallback() {
    for (const timer of this._timers) clearTimeout(timer);
    this._timers.clear();
  }

  // ---- data ---------------------------------------------------------------

  _entityId(platform, key) {
    return `${platform}.${this._config.entity_prefix}_${key}`;
  }

  _sourceStates() {
    const states = (this._hass && this._hass.states) || {};
    return Object.values(SOURCES).map(([platform, key]) => states[this._entityId(platform, key)]);
  }

  _list(source) {
    const [platform, key, attribute] = SOURCES[source];
    const state = this._hass.states[this._entityId(platform, key)];
    const value = state && state.attributes ? state.attributes[attribute] : null;
    return Array.isArray(value) ? value : [];
  }

  _pruneHandled(dataChanged) {
    const now = Date.now();
    for (const [key, at] of this._handled) {
      const age = now - at;
      if (age > OPTIMISTIC_MAX_MS || (dataChanged && age > OPTIMISTIC_MIN_MS)) {
        this._handled.delete(key);
      }
    }
  }

  _isHidden(type, id) {
    return this._handled.has(`${type}:${id}`);
  }

  _collect() {
    const cfg = this._config;
    const locations = { ...DEFAULT_LOCATIONS, ...(cfg.locations || {}) };
    const now = new Date();
    const overdue = [];
    const pantry = {};
    const chores = [];
    const tasks = [];
    const shopping = [];

    for (const task of this._list("tasks")) {
      if (task.done || this._isHidden("task", task.id)) continue;
      const days = daysUntil(task.due_date, now);
      const item = {
        type: "task", id: task.id, name: task.name || `Task ${task.id}`,
        meta: dueText(task.due_date, now), overdue: days !== null && days < 0,
      };
      (item.overdue ? overdue : tasks).push(item);
    }

    for (const chore of this._list("chores")) {
      if (this._isHidden("chore", chore.id)) continue;
      const when = chore.next_estimated_execution_time;
      const days = daysUntil(when, now);
      const date = parseDate(when);
      chores.push({
        type: "chore", id: chore.id, name: chore.name || chore.chore_name || `Chore ${chore.id}`,
        meta: dueText(when, now),
        overdue: days !== null && (days < 0 || (days === 0 && !chore.track_date_only && date && date < now)),
      });
    }

    for (const battery of this._list("batteries")) {
      if (this._isHidden("battery", battery.id)) continue;
      overdue.push({
        type: "battery", id: battery.id, name: battery.name || `Battery ${battery.id}`,
        meta: dueText(battery.next_estimated_charge_time, now), overdue: true,
      });
    }

    for (const product of this._list("stock")) {
      const id = product.id ?? product.product_id;
      if (id === undefined || this._isHidden("product", id)) continue;
      const days = daysUntil(product.best_before_date, now);
      const amount = product.available_amount ?? product.amount_aggregated ?? product.amount;
      const item = {
        type: "product", id, name: product.name || (product.product && product.product.name) || `Product ${id}`,
        meta: dueText(product.best_before_date, now),
        overdue: days !== null && days < 0,
        expiring: days !== null && days >= 0 && days <= 3,
        lead: `${formatAmount(amount)}${shortUnit(product.default_quantity_unit_purchase && product.default_quantity_unit_purchase.name)}`,
        picture: cfg.show_pictures ? product.picture_url : null,
      };
      if (item.overdue) {
        overdue.push(item);
      } else {
        const location = locations[product.location_id] || (product.location_id ? `Location ${product.location_id}` : "Stock");
        (pantry[location] = pantry[location] || []).push(item);
      }
    }

    for (const entry of this._list("shopping")) {
      // Notes without a product can't be removed by product ID.
      if (entry.done || !entry.product_id || this._isHidden("shopping", entry.product_id)) continue;
      shopping.push({
        type: "shopping", id: entry.product_id,
        name: (entry.product && entry.product.name) || `Product ${entry.product_id}`,
        meta: entry.note || "", amount: Number(entry.amount) || 1,
        lead: `${formatAmount(entry.amount || 1)}x`,
      });
    }

    return { overdue, pantry, chores, tasks, shopping };
  }

  // ---- rendering ----------------------------------------------------------

  _notice() {
    const states = this._sourceStates();
    if (states.every((state) => !state)) {
      const id = this._entityId("sensor", "stock");
      return `<div class="notice">No Grocy Pro entities found (looked for <code>${esc(id)}</code> and friends).
        Is Grocy Pro set up? If you renamed the entities, set <code>entity_prefix</code> in the card.</div>`;
    }
    if (states.some((state) => state && state.state === "unavailable")) {
      return `<div class="notice">Grocy is not reachable right now. Lists may be incomplete.</div>`;
    }
    return "";
  }

  _section(title, icon, items) {
    let body;
    if (!items.length) {
      body = `<div class="empty">All clear \u2705</div>`;
    } else {
      body = `<div class="items">${items.map((item) => this._item(item)).join("")}</div>`;
    }
    return `<section>
      <div class="section-label"><ha-icon icon="${esc(icon)}"></ha-icon><span>${esc(title)}</span>
        <span class="count">${items.length || ""}</span></div>
      ${body}
    </section>`;
  }

  _button(action, item, label, cls = "", extra = "") {
    const busy = this._busy.has(`${item.type}:${item.id}`);
    return `<button class="${cls}" data-action="${esc(action)}" data-type="${esc(item.type)}"
      data-id="${esc(item.id)}" ${extra} ${busy ? "disabled" : ""}>${esc(label)}</button>`;
  }

  _item(item) {
    const icons = { task: "mdi:clipboard-check-outline", chore: "mdi:broom", battery: "mdi:battery-alert" };
    let lead;
    if (item.picture) {
      lead = `<div class="lead"><img src="${esc(item.picture)}?width=96" alt="" loading="lazy"></div>`;
    } else if (icons[item.type]) {
      lead = `<div class="lead"><ha-icon icon="${icons[item.type]}"></ha-icon></div>`;
    } else {
      lead = `<div class="lead">${esc(item.lead || "")}</div>`;
    }

    let buttons = "";
    if (item.type === "task") {
      buttons = this._button("complete_task", item, "Done", "green")
        + this._button("delete", item, "", "icon", `title="Delete task" aria-label="Delete task" data-object="tasks"`);
    } else if (item.type === "chore") {
      buttons = this._button("execute_chore", item, "Done", "green")
        + this._button("delete", item, "", "icon", `title="Delete chore" aria-label="Delete chore" data-object="chores"`);
    } else if (item.type === "battery") {
      buttons = this._button("track_battery", item, "Charged", "amber");
    } else if (item.type === "shopping") {
      buttons = this._button("remove_shopping", item, "Remove", "red", `data-amount="${esc(item.amount)}"`);
    } else if (item.type === "product") {
      buttons = item.overdue
        ? this._button("waste", item, "Waste", "red")
        : this._button("open_product", item, "Open", "amber") + this._button("consume", item, "Consume");
    }
    buttons = buttons.replace(/<button class="icon"([^>]*)><\/button>/g,
      '<button class="icon"$1><ha-icon icon="mdi:delete-outline"></ha-icon></button>');

    const state = item.overdue ? "overdue" : item.expiring ? "expiring" : "";
    return `<div class="item ${state}">
      ${lead}
      <div class="details"><span class="name">${esc(item.name)}</span>
        ${item.meta ? `<span class="meta ${state}">${esc(item.meta)}</span>` : ""}</div>
      <div class="actions">${buttons}</div>
    </div>`;
  }

  _render() {
    if (!this._hass) return;
    this._pruneHandled(false);
    const data = this._collect();
    const pantryCount = Object.values(data.pantry).reduce((n, list) => n + list.length, 0);
    const active = pantryCount + data.chores.length + data.tasks.length + data.shopping.length;

    const left = [];
    if (data.overdue.length) left.push(this._section("Action required", "mdi:alert-circle-outline", data.overdue));
    const locations = Object.keys(data.pantry).sort();
    for (const location of locations) {
      const lower = location.toLowerCase();
      const icon = lower.includes("fridge") ? "mdi:fridge-outline"
        : lower.includes("freez") ? "mdi:snowflake"
          : lower.includes("cupboard") ? "mdi:cupboard-outline"
            : "mdi:food-apple-outline";
      left.push(this._section(location, icon, data.pantry[location]));
    }
    if (!locations.length) left.push(this._section("Pantry", "mdi:food-apple-outline", []));

    const right = [
      this._section("Shopping list", "mdi:cart-outline", data.shopping),
      this._section("Chores", "mdi:broom", data.chores),
      this._section("Tasks", "mdi:clipboard-check-outline", data.tasks),
    ];

    const log = this._config.show_log && this._log.length
      ? `<div class="log">${this._log.map((l) => `<div class="${l.cls}">${esc(l.text)}</div>`).join("")}</div>`
      : "";

    this._root.innerHTML = `
      <div class="header">
        <div class="title"><ha-icon icon="mdi:food-apple"></ha-icon><span>${esc(this._config.title)}</span></div>
        <div class="badges">
          <span class="badge red"><span class="dot"></span>${data.overdue.length} overdue</span>
          <span class="badge green"><span class="dot"></span>${active} active</span>
        </div>
      </div>
      ${this._notice()}
      <div class="grid">
        <div class="column">${left.join("")}</div>
        <div class="column">${right.join("")}</div>
      </div>
      ${log}`;
  }

  // ---- actions ------------------------------------------------------------

  _addLog(text, cls = "") {
    const time = new Date().toLocaleTimeString();
    this._log.push({ text: `${time}  ${text}`, cls });
    while (this._log.length > LOG_LINES) this._log.shift();
  }

  _onClick(ev) {
    const button = ev.target.closest("button[data-action]");
    if (!button || button.disabled) return;
    const { action, type, object } = button.dataset;
    const id = Number(button.dataset.id);
    if (!Number.isFinite(id)) return;
    const item = { type, id, name: button.closest(".item").querySelector(".name").textContent };

    const calls = {
      complete_task: ["complete_task", { task_id: id }, "completed"],
      execute_chore: ["execute_chore", { chore_id: id }, "done"],
      track_battery: ["track_battery", { battery_id: id }, "charged"],
      consume: ["consume_product_from_stock", { product_id: id, amount: 1, spoiled: false, transaction_type: "consume" }, "consumed (1)"],
      waste: ["consume_product_from_stock", { product_id: id, amount: 1, spoiled: true, transaction_type: "consume" }, "thrown away (1)"],
      open_product: ["open_product", { product_id: id, amount: 1 }, "opened (1)"],
      remove_shopping: ["remove_product_in_shopping_list", { product_id: id, list_id: 1, amount: Number(button.dataset.amount) || 1 }, "removed from the shopping list"],
      delete: ["delete_generic", { entity_type: object, object_id: id }, "deleted"],
    };
    const call = calls[action];
    if (!call) return;
    if (action === "delete" && this._config.confirm_delete) {
      // eslint-disable-next-line no-alert
      if (!window.confirm(`Delete "${item.name}" from Grocy? This can't be undone.`)) return;
    }
    // Opening doesn't remove the item from the list; everything else does.
    this._run(item, call[0], call[1], call[2], action !== "open_product");
  }

  async _run(item, service, data, verb, hide) {
    const key = `${item.type}:${item.id}`;
    this._busy.add(key);
    this._render();
    try {
      await this._hass.callService(this._config.domain, service, data);
      if (hide) this._handled.set(key, Date.now());
      this._addLog(`${item.name}: ${verb}`, "ok");
    } catch (err) {
      const message = (err && (err.message || err.code)) || "unknown error";
      this._addLog(`${item.name}: failed (${message})`, "err");
    } finally {
      this._busy.delete(key);
      this._render();
    }
    if (hide) {
      // Show the item again if Grocy Pro never sends updated data.
      const timer = setTimeout(() => {
        this._timers.delete(timer);
        this._pruneHandled(false);
        this._render();
      }, OPTIMISTIC_MAX_MS + 1000);
      this._timers.add(timer);
    }
  }
}

const EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  { name: "entity_prefix", selector: { text: {} } },
  { name: "show_pictures", selector: { boolean: {} } },
  { name: "show_log", selector: { boolean: {} } },
  { name: "confirm_delete", selector: { boolean: {} } },
];

const EDITOR_LABELS = {
  title: "Title",
  entity_prefix: "Entity prefix (sensor.<prefix>_stock)",
  show_pictures: "Show product pictures",
  show_log: "Show the action log",
  confirm_delete: "Ask before deleting tasks and chores",
};

class GrocyActionCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...(config || {}) };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        const config = { ...this._config, ...ev.detail.value };
        for (const [key, value] of Object.entries(config)) {
          if (key !== "type" && DEFAULTS[key] === value) delete config[key];
        }
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = { ...DEFAULTS, ...this._config };
  }
}

// Loaded automatically by the Grocy Pro integration. Guard against a second
// copy (an old /local/grocy-action-card.js resource) defining it twice.
if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, GrocyActionCard);
  customElements.define(EDITOR_TAG, GrocyActionCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TAG,
    name: "Grocy Pro Command Center",
    description: "Stock, chores, tasks, batteries and the shopping list from Grocy Pro, with one-tap actions.",
    preview: false,
    documentationURL: "https://github.com/DonTranQuiL/grocy-pro#dashboard-card",
  });
} else if (!customElements.get(EDITOR_TAG)) {
  // Another copy (usually an old /local/grocy-action-card.js dashboard
  // resource from 2.x) got here first and is the one being shown.
  console.warn(
    "Grocy Pro: an older grocy-action-card is already loaded, so the card that comes "
    + "with the integration is not used. Remove the /local/grocy-action-card.js resource "
    + "(Settings > Dashboards > Resources) and the file in /config/www, then reload."
  );
}

(() => {
  let version = "";
  try {
    version = new URL(import.meta.url).searchParams.get("v") || "";
  } catch (err) {
    // no version information
  }
  console.info(`%c GROCY PRO CARD %c ${version}`, "color:#0b1120;background:#ffb52e;font-weight:700", "color:#46e1ff");
})();
