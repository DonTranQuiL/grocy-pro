class GrocyActionCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;

    // The Optimistic Cache
    if (!this.processedItems) {
      this.processedItems = new Set();
    }

    if (!this.content) {
      this.innerHTML = `
        <ha-card class="grocy-card">
          <div class="header">
            <div class="title">
              <ha-icon icon="mdi:check-all"></ha-icon>
              <span>Grocy Command Center</span>
            </div>
          </div>
          <div id="content"></div>

          <style>
            .grocy-card {
              border-radius: 24px;
              overflow: hidden;
            }
            .header {
              padding: 20px;
              background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
              color: white;
            }
            .title {
              display: flex;
              align-items: center;
              gap: 12px;
              font-size: 1.4rem;
              font-weight: 600;
            }
            #content {
              padding: 16px;
            }
            .stats {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
              gap: 12px;
              margin-bottom: 20px;
            }
            .stat {
              background: var(--card-background-color);
              border-radius: 16px;
              padding: 12px;
              text-align: center;
              border: 1px solid rgba(255, 255, 255, 0.08);
            }
            .stat-number {
              font-size: 1.4rem;
              font-weight: bold;
            }
            .stat-label {
              opacity: 0.7;
              font-size: 0.8rem;
              white-space: nowrap;
            }
            .danger .stat-number {
              color: var(--error-color);
            }
            .dashboard {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
              gap: 16px;
            }
            .section {
              background: var(--card-background-color);
              border-radius: 18px;
              overflow: hidden;
              border: 1px solid rgba(255, 255, 255, 0.08);
            }
            .section-header {
              display: flex;
              align-items: center;
              gap: 10px;
              padding: 14px 18px;
              font-weight: 600;
              border-bottom: 1px solid var(--divider-color);
            }
            .section.overdue .section-header {
              color: var(--error-color);
            }
            .item {
              display: flex;
              justify-content: space-between;
              align-items: center;
              gap: 12px;
              padding: 14px 18px;
              border-bottom: 1px solid var(--divider-color);
              transition: background .2s;
              flex-wrap: wrap;
            }
            .item:hover {
              background: rgba(255, 255, 255, 0.04);
            }
            .item:last-child {
              border-bottom: none;
            }
            .item-left {
              display: flex;
              align-items: center;
              gap: 12px;
              flex: 1;
              min-width: 150px;
            }
            .item-info {
              display: flex;
              flex-direction: column;
              overflow: hidden;
            }
            .item-title {
              font-weight: 500;
              white-space: normal;
              word-break: break-word;
            }
            .item-date {
              font-size: 0.8rem;
              color: var(--secondary-text-color);
            }
            .overdue-text {
              color: var(--error-color);
            }
            .actions {
              display: flex;
              gap: 8px;
              flex-wrap: wrap;
              align-items: center;
              justify-content: flex-end;
            }
            .btn {
              background: transparent;
              border: 1px solid var(--primary-color);
              color: var(--primary-color);
              padding: 6px 12px;
              border-radius: 6px;
              cursor: pointer;
              font-weight: 600;
              font-size: 0.8rem;
              transition: all 0.2s ease;
              font-family: inherit;
              outline: none;
            }
            .btn:hover {
              background: var(--primary-color);
              color: white;
            }
            .btn.waste {
              border-color: var(--error-color);
              color: var(--error-color);
            }
            .btn.waste:hover {
              background: var(--error-color);
              color: white;
            }
            .btn.open {
              border-color: var(--info-color);
              color: var(--info-color);
            }
            .btn.open:hover {
              background: var(--info-color);
              color: white;
            }
            .btn:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }
            .delete-btn {
              color: var(--error-color);
              opacity: 0.6;
              cursor: pointer;
              padding: 4px;
              border-radius: 50%;
              transition: background 0.2s, opacity 0.2s;
              display: flex;
              align-items: center;
              justify-content: center;
            }
            .delete-btn:hover {
              opacity: 1;
              background: rgba(255, 0, 0, 0.1);
            }
            .empty {
              padding: 20px;
              text-align: center;
              color: var(--secondary-text-color);
            }
            @media (max-width: 800px) {
              .dashboard { grid-template-columns: 1fr; }
            }
          </style>
        </ha-card>
      `;
      this.content = this.querySelector("#content");
    }

    this.render();
  }

  // FIXED: Now checks for both lowercase and Capitalized attributes
  getAttr(entityId, attrName) {
    const entity = this._hass.states[entityId];
    if (!entity || !entity.attributes) return [];
    const Capitalized = attrName.charAt(0).toUpperCase() + attrName.slice(1);
    return entity.attributes[attrName] || entity.attributes[Capitalized] || [];
  }

  relativeDate(date) {
    if (!date) return "";
    const diff = Math.floor((new Date(date) - new Date()) / 86400000);
    if (diff < 0) return `${Math.abs(diff)} day(s) overdue`;
    if (diff === 0) return "Due today";
    if (diff === 1) return "Due tomorrow";
    return `Due in ${diff} day(s)`;
  }

  render() {
    const chores = this.getAttr('sensor.grocy_chores', 'chores');
    const tasks = this.getAttr('sensor.grocy_tasks', 'tasks');
    const stock = this.getAttr('sensor.grocy_stock', 'products');
    const shoppingList = this.getAttr('sensor.grocy_shopping_list', 'products');
    const overdueBatteries = this.getAttr('binary_sensor.grocy_overdue_batteries', 'overdue_batteries');

    const getProductName = (id) => {
      const item = stock.find(s => s.product_id == id || s.id == id);
      if (item?.product?.name) return item.product.name;
      if (item?.name) return item.name;
      return `Product #${id}`;
    };

    const overdueItems = [];
    const taskItems = [];
    const choreItems = [];
    const shoppingItems = [];
    
    // --- THE SMART LOCATION MAPPING ---
    const locationNames = {
      1: "Pantry",
      2: "Fridge",
      3: "Freezer",
      4: "Cupboards"
      // Add more IDs here as you create locations in Grocy!
    };
    
    // We will dynamically group the food into this object
    const foodByLocation = {};

    // Process Tasks
    tasks.forEach(task => {
      if (this.processedItems.has('task_' + task.id)) return;
      const overdueFlag = task.due_date && new Date(task.due_date) < new Date();
      const item = { id: task.id, title: task.name || "Task", date: task.due_date, overdue: overdueFlag, type: "task" };
      if (overdueFlag) overdueItems.push(item); else taskItems.push(item);
    });

    // Process Chores
    chores.forEach(chore => {
      if (this.processedItems.has('chore_' + chore.id)) return;
      const overdueFlag = new Date(chore.next_estimated_execution_time) < new Date();
      const item = { id: chore.id, title: chore.name || chore.chore?.name || "Chore", date: chore.next_estimated_execution_time, overdue: overdueFlag, type: "chore" };
      if (overdueFlag) overdueItems.push(item); else choreItems.push(item);
    });

    // Process Batteries (Overdue)
    overdueBatteries.forEach(battery => {
      if (this.processedItems.has('battery_' + battery.id)) return;
      overdueItems.push({ 
        id: battery.id, 
        title: battery.battery?.name || battery.name || "Battery", 
        date: battery.next_estimated_charge_time, 
        overdue: true, 
        type: "battery" 
      });
    });

    // Process Food & Sort by Location
    const foodSet = new Set();
    stock.forEach(food => {
      const id = food.product_id || food.id;
      if (this.processedItems.has('food_' + id)) return;
      if (foodSet.has(id)) return;
      foodSet.add(id);

      const overdueFlag = new Date(food.best_before_date) < new Date();
      const item = { id, title: getProductName(id), date: food.best_before_date, overdue: overdueFlag, type: "food" };
      
      if (overdueFlag) {
        overdueItems.push(item); 
      } else {
        // Group the good food by its location ID
        const locId = food.location_id || 1;
        const locName = locationNames[locId] || `Storage #${locId}`;
        
        if (!foodByLocation[locName]) {
          foodByLocation[locName] = [];
        }
        foodByLocation[locName].push(item);
      }
    });

    // Process Shopping List
    shoppingList.forEach(s => {
      const pId = s.product_id;
      if (this.processedItems.has('shopping_' + pId)) return;
      shoppingItems.push({
        id: pId,
        title: `${s.amount}x ${getProductName(pId)}`,
        date: s.note ? `Note: ${s.note}` : null,
        overdue: false,
        type: "shopping"
      });
    });

    // Calculate total food count for stats
    let totalFood = 0;
    Object.values(foodByLocation).forEach(arr => totalFood += arr.length);
    const total = overdueItems.length + taskItems.length + choreItems.length + totalFood + shoppingItems.length;

    const section = (title, icon, items, overdueSection = false) => {
      let html = `
      <div class="section ${overdueSection ? 'overdue' : ''}">
        <div class="section-header">
          <ha-icon icon="${icon}"></ha-icon>
          ${title}
        </div>
      `;

      if (!items || !items.length) {
        html += `<div class="empty">Nothing here 🎉</div>`;
      } else {
        items.forEach(item => {
          let buttons = "";
          let hardDeleteHtml = "";
          let rowIcon = "mdi:check";

          if (item.type === "task") {
            rowIcon = "mdi:clipboard-check-outline";
            buttons = `<button class="btn action-btn" data-action="task" data-id="${item.id}">Done</button>`;
            hardDeleteHtml = `<div class="delete-btn action-btn" data-action="delete" data-id="${item.id}" data-type="tasks" title="Delete Task"><ha-icon style="pointer-events: none;" icon="mdi:delete-outline"></ha-icon></div>`;
          } 
          else if (item.type === "chore") {
            rowIcon = "mdi:broom";
            buttons = `<button class="btn action-btn" data-action="chore" data-id="${item.id}">Done</button>`;
            hardDeleteHtml = `<div class="delete-btn action-btn" data-action="delete" data-id="${item.id}" data-type="chores" title="Delete Chore"><ha-icon style="pointer-events: none;" icon="mdi:delete-outline"></ha-icon></div>`;
          } 
          else if (item.type === "battery") {
            rowIcon = "mdi:battery-alert";
            buttons = `<button class="btn action-btn" data-action="battery" data-id="${item.id}">Charge</button>`;
          }
          else if (item.type === "shopping") {
            rowIcon = "mdi:cart-outline";
            buttons = `<button class="btn action-btn" data-action="shopping" data-id="${item.id}">Remove</button>`;
          }
          else if (item.type === "food") {
            rowIcon = "mdi:food-apple";
            if (item.overdue) {
              buttons = `<button class="btn waste action-btn" data-action="consume" data-id="${item.id}" data-spoiled="true">Waste</button>`;
            } else {
              buttons = `
                <button class="btn open action-btn" data-action="open" data-id="${item.id}">Open</button>
                <button class="btn action-btn" data-action="consume" data-id="${item.id}" data-spoiled="false">Consume</button>
              `;
            }
          }

          html += `
            <div class="item">
              <div class="item-left">
                <ha-icon icon="${rowIcon}"></ha-icon>
                <div class="item-info">
                  <div class="item-title">${item.title}</div>
                  <div class="item-date ${item.overdue ? 'overdue-text' : ''}">${item.type === 'shopping' && item.date ? item.date : this.relativeDate(item.date)}</div>
                </div>
              </div>
              <div class="actions">
                ${buttons}
                ${hardDeleteHtml}
              </div>
            </div>
          `;
        });
      }
      html += `</div>`;
      return html;
    };

    // Base Dashboard with static lists
    let dashboardHtml = `
      ${section("Action Required", "mdi:alert-circle", overdueItems, true)}
      ${section("Shopping List", "mdi:cart", shoppingItems)}
      ${section("Tasks", "mdi:clipboard-check", taskItems)}
      ${section("Chores", "mdi:broom", choreItems)}
    `;

    // Dynamically append the Food Locations!
    Object.keys(foodByLocation).sort().forEach(locName => {
      // Smart Icon logic based on the name of the location
      let icon = "mdi:package-variant-closed"; // default
      if (locName.toLowerCase().includes("fridge")) icon = "mdi:fridge-outline";
      if (locName.toLowerCase().includes("freez")) icon = "mdi:snowflake";
      if (locName.toLowerCase().includes("pantry")) icon = "mdi:food-apple";
      if (locName.toLowerCase().includes("cupboard")) icon = "mdi:cupboard";
      
      dashboardHtml += section(locName, icon, foodByLocation[locName]);
    });

    this.content.innerHTML = `
      <div class="stats">
        <div class="stat"><div class="stat-number">${total}</div><div class="stat-label">Total</div></div>
        <div class="stat danger"><div class="stat-number">${overdueItems.length}</div><div class="stat-label">Overdue</div></div>
        <div class="stat"><div class="stat-number">${totalFood}</div><div class="stat-label">Food</div></div>
        <div class="stat"><div class="stat-number">${shoppingItems.length}</div><div class="stat-label">Cart</div></div>
        <div class="stat"><div class="stat-number">${choreItems.length}</div><div class="stat-label">Chores</div></div>
      </div>
      <div class="dashboard">
        ${dashboardHtml}
      </div>
    `;

    // Bind all the new actions
    this.content.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        
        if (action === 'task') this.completeTask(id, btn);
        else if (action === 'chore') this.executeChore(id, btn);
        else if (action === 'consume') this.consumeFood(id, btn.dataset.spoiled === 'true', btn);
        else if (action === 'open') this.openFood(id, btn);
        else if (action === 'delete') this.deleteItem(id, btn.dataset.type, btn);
        else if (action === 'battery') this.trackBattery(id, btn);
        else if (action === 'shopping') this.removeShoppingItem(id, btn);
      });
    });
  }

  // --- ACTIONS (OPTIMISTIC CACHE) ---

  executeChore(id, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "execute_chore", { chore_id: parseInt(id) })
      .then(() => { this.processedItems.add('chore_' + id); this.render(); })
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  completeTask(id, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "complete_task", { task_id: parseInt(id) })
      .then(() => { this.processedItems.add('task_' + id); this.render(); })
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  consumeFood(id, spoiled, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "consume_product_from_stock", { product_id: parseInt(id), amount: 1, spoiled: spoiled, transaction_type: "CONSUME" })
      .then(() => { this.processedItems.add('food_' + id); this.render(); })
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  openFood(id, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "open_product", { product_id: parseInt(id), amount: 1 })
      .then(() => { btn.innerText = "Opened"; }) // Opening doesn't necessarily hide it, just marks it open
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  trackBattery(id, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "track_battery", { battery_id: parseInt(id) })
      .then(() => { this.processedItems.add('battery_' + id); this.render(); })
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  removeShoppingItem(id, btn) {
    btn.disabled = true; btn.innerText = "...";
    this._hass.callService("grocy", "remove_product_in_shopping_list", { product_id: parseInt(id) })
      .then(() => { this.processedItems.add('shopping_' + id); this.render(); })
      .catch(() => { btn.disabled = false; btn.innerText = "Error"; });
  }

  deleteItem(id, entityType, iconDiv) {
    iconDiv.style.pointerEvents = "none"; iconDiv.style.opacity = "0.2";
    this._hass.callService("grocy", "delete_generic", { entity_type: entityType, object_id: parseInt(id) })
      .then(() => {
        const prefix = entityType === 'tasks' ? 'task_' : entityType === 'chores' ? 'chore_' : 'food_';
        this.processedItems.add(prefix + id);
        this.render();
      }).catch(() => { iconDiv.style.pointerEvents = "auto"; iconDiv.style.opacity = "0.6"; });
  }

  setConfig(config) { this.config = config; }
  getCardSize() { return 10; }
}

customElements.define("grocy-action-card", GrocyActionCard);
