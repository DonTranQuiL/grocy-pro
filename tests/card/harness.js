// Browser test harness for the Grocy Pro card. Runs in headless Chrome
// (see tests/test_card.py) after the card module; writes JSON results to #out.
const results = { errors: [], calls: [], checks: {} };
const origError = console.error;
console.error = (...args) => { results.errors.push(args.map(String).join(" ")); origError(...args); };
window.addEventListener("error", (ev) => results.errors.push(String(ev.message)));
window.addEventListener("unhandledrejection", (ev) => results.errors.push(String(ev.reason)));

// Minimal stand-in for Home Assistant's form element used by the editor.
customElements.define("ha-form", class extends HTMLElement {});

const STATES = JSON.parse(document.getElementById("states").textContent);
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

function makeHass(states, fail = false) {
  return {
    states,
    callService: async (domain, service, data) => {
      results.calls.push({ domain, service, data });
      if (fail) throw new Error("boom <b>bold</b>");
    },
  };
}

function texts(card) {
  return card.shadowRoot.querySelector(".wrap").textContent.replace(/\s+/g, " ");
}

function itemNames(card) {
  return [...card.shadowRoot.querySelectorAll(".item .name")].map((el) => el.textContent);
}

async function newCard(config, states, width = 900) {
  const box = document.createElement("div");
  box.style.width = `${width}px`;
  document.body.appendChild(box);
  const card = document.createElement("grocy-action-card");
  card.setConfig(config);
  box.appendChild(card);
  card.hass = makeHass(states);
  await flush();
  return card;
}

async function click(card, selector) {
  const button = card.shadowRoot.querySelector(selector);
  if (!button) return false;
  button.click();
  await flush();
  await flush();
  return true;
}

(async () => {
  const c = results.checks;
  try {
    const card = await newCard({}, STATES);
    const text = texts(card);
    c.items = itemNames(card).length;
    c.names = itemNames(card);
    c.bad_text = ["??", "undefined", "NaN", "null", "[object Object]"].filter((t) => text.includes(t));
    c.has_check_emoji = text.includes("\u2705");
    c.sections = [...card.shadowRoot.querySelectorAll(".section-label span:first-of-type")].map((el) => el.textContent);
    c.pictures = card.shadowRoot.querySelectorAll(".lead img").length;
    c.wide_columns = getComputedStyle(card.shadowRoot.querySelector(".grid")).gridTemplateColumns.split(" ").length;

    // Same state objects again: no re-render.
    let renders = 0;
    const realRender = card._render.bind(card);
    card._render = () => { renders += 1; realRender(); };
    card.hass = makeHass(STATES);
    c.renders_on_same_states = renders;
    card.hass = makeHass({ ...STATES, "sensor.unrelated": { state: "1", attributes: {} } });
    c.renders_on_unrelated_change = renders;
    card._render = realRender;

    // Every action type, once.
    const before = itemNames(card).length;
    const actions = ["consume", "waste", "open_product", "complete_task", "execute_chore", "track_battery", "remove_shopping"];
    c.clicked = [];
    for (const action of actions) {
      if (await click(card, `button[data-action="${action}"]`)) c.clicked.push(action);
    }
    c.hidden_after_actions = before - itemNames(card).length;
    c.log_lines = card.shadowRoot.querySelectorAll(".log div").length;

    // Delete asks first; "cancel" sends nothing.
    window.confirm = () => false;
    const callsBefore = results.calls.length;
    await click(card, 'button[data-action="delete"]');
    c.delete_cancel_calls = results.calls.length - callsBefore;
    window.confirm = () => true;
    c.clicked_delete = await click(card, 'button[data-action="delete"]');

    // Fresh data arrives: handled items older than 2 s may come back.
    card._handled.forEach((_, key) => card._handled.set(key, Date.now() - 5000));
    card.hass = makeHass({ ...STATES });
    const fresh = {};
    for (const [id, state] of Object.entries(STATES)) fresh[id] = { ...state };
    card.hass = makeHass(fresh);
    c.items_after_refresh = itemNames(card).length;

    // Errors are logged (escaped) and the button is usable again.
    card.hass = { ...makeHass(fresh, true) };
    card._hass = makeHass(fresh, true);
    await click(card, 'button[data-action="consume"]');
    const lastLog = [...card.shadowRoot.querySelectorAll(".log div")].pop();
    c.error_logged = lastLog ? lastLog.textContent : "";
    c.error_has_markup = card.shadowRoot.querySelectorAll(".log b").length;
    const retry = card.shadowRoot.querySelector('button[data-action="consume"]');
    c.button_enabled_after_error = retry ? !retry.disabled : null;

    // Disconnect clears timers.
    card.parentElement.remove();
    c.timers_after_disconnect = card._timers.size;

    // HTML in names is shown as text.
    const evil = JSON.parse(JSON.stringify(STATES));
    evil["sensor.grocy_stock"].attributes.products[0].name = '<img src="x" onerror="window.__xss=1">';
    evil["sensor.grocy_stock"].attributes.products[0].picture_url = '" onerror="window.__xss=2';
    const xss = await newCard({ title: "<b>T</b>", locations: { 4: "<i>Cup</i>" } }, evil);
    c.xss_img = xss.shadowRoot.querySelectorAll('img[src="x"], b, i').length;
    c.xss_text = texts(xss).includes('<img src="x"');
    c.xss_fired = window.__xss || 0;

    // Missing and unavailable entities.
    const missing = await newCard({ entity_prefix: "nope" }, STATES);
    c.missing_notice = texts(missing).includes("No Grocy Pro entities found");
    const down = JSON.parse(JSON.stringify(STATES));
    down["sensor.grocy_stock"] = { state: "unavailable", attributes: {} };
    const unavailable = await newCard({}, down);
    c.unavailable_notice = texts(unavailable).includes("not reachable");
    c.unavailable_errors = results.errors.length;

    // Narrow card: one column, actions wrap.
    const narrow = await newCard({}, STATES, 360);
    c.narrow_columns = getComputedStyle(narrow.shadowRoot.querySelector(".grid")).gridTemplateColumns.split(" ").length;
    const firstItem = narrow.shadowRoot.querySelector(".item");
    c.narrow_overflow = firstItem ? firstItem.scrollWidth > firstItem.clientWidth + 1 : null;

    // Config validation and editor.
    try { document.createElement("grocy-action-card").setConfig("nope"); c.bad_config = "accepted"; } catch (err) { c.bad_config = "rejected"; }
    const Card = customElements.get("grocy-action-card");
    c.stub = Card.getStubConfig();
    const editor = Card.getConfigElement();
    let changed = null;
    editor.addEventListener("config-changed", (ev) => { changed = ev.detail.config; });
    editor.setConfig({ type: "custom:grocy-action-card" });
    editor.hass = makeHass(STATES);
    const form = editor.querySelector("ha-form");
    c.editor_fields = form ? form.schema.map((s) => s.name) : [];
    c.editor_label = form ? form.computeLabel({ name: "entity_prefix" }) : "";
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, title: "Kitchen", show_log: false } } }));
    c.editor_config = changed;
  } catch (err) {
    results.errors.push(`harness: ${err && err.stack ? err.stack : err}`);
  }
  document.getElementById("out").textContent = JSON.stringify(results);
})();
