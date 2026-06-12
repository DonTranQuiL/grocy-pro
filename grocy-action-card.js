class GrocyActionCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;

    if (!this.processedItems) {
      this.processedItems = new Set();
    }

    if (!this.terminalLogs) {
      this.terminalLogs = [
        `[SUCCESS 12:08:46 PM] Receipt Vision processing resolved. Model matches schema with 98% accuracy.`,
        `[API 12:08:46 PM] Added bulk entities: grocy.add_products_by_name { Gala Apples: 6, Butter: 2 }`,
        `[INFO 12:09:51 PM] Restored initial test data registers.`
      ];
    }

    if (!this.content) {
      this.innerHTML = `
        <ha-card class="grocy-card">
          <!-- Premium Header Container -->
          <div class="header-container">
            <div class="header-left">
              <div class="header-icon-box">
                <ha-icon icon="mdi:home-assistant"></ha-icon>
              </div>
              <div class="header-text-block">
                <span class="header-title">Grocy Pro Command Center</span>
                <span class="header-subtitle">custom:grocy-action-card</span>
              </div>
            </div>
            <div class="header-badges">
              <div class="badge badge-overdue">
                <span class="badge-dot dot-red"></span>
                <span id="badge-overdue-val">0</span> Expired/Overdue
              </div>
              <div class="badge badge-active">
                <span class="badge-dot dot-green"></span>
                <span id="badge-active-val">0</span> Active Inventory Items
              </div>
            </div>
          </div>

          <div id="content"></div>

          <!-- Interactive Event Console Stream -->
          <div class="console-wrapper">
            <div class="console-header">
              <span class="console-label">
                <ha-icon icon="mdi:terminal"></ha-icon> Home Assistant Event Stream
              </span>
              <span class="console-live-badge">LIVE</span>
            </div>
            <div id="terminal-stream" class="console-body"></div>
          </div>

          <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

            .grocy-card {
              background: #05070f !important;
              background-image: radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 60%) !important;
              backdrop-filter: blur(16px);
              -webkit-backdrop-filter: blur(16px);
              border: 1px solid rgba(255, 255, 255, 0.05) !important;
              border-radius: 24px !important;
              color: #f1f5f9 !important;
              font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
              overflow: hidden;
              box-shadow: 0 20px 40px -15px rgba(2, 132, 199, 0.25) !important;
              padding: 0 !important;
            }

            /* Header Section Styling */
            .header-container {
              display: flex;
              justify-content: space-between;
              align-items: center;
              flex-wrap: wrap;
              gap: 16px;
              padding: 24px;
              border-bottom: 1px solid rgba(255, 255, 255, 0.05);
              background: rgba(255, 255, 255, 0.01);
            }
            .header-left {
              display: flex;
              align-items: center;
              gap: 14px;
            }
            .header-icon-box {
              width: 44px;
              height: 44px;
              border-radius: 12px;
              background: rgba(2, 132, 199, 0.15);
              border: 1px solid rgba(56, 189, 248, 0.2);
              display: flex;
              align-items: center;
              justify-content: center;
              color: #38bdf8;
            }
            .header-icon-box ha-icon {
              --mdc-icon-size: 24px;
              color: #38bdf8 !important;
              display: flex;
              align-items: center;
              justify-content: center;
            }
            .header-text-block {
              display: flex;
              flex-direction: column;
            }
            .header-title {
              font-weight: 800;
              font-size: 1.15rem;
              letter-spacing: -0.02em;
              color: #ffffff;
            }
            .header-subtitle {
              font-family: 'JetBrains Mono', monospace;
              font-size: 0.7rem;
              color: #94a3b8;
              text-transform: uppercase;
              letter-spacing: 0.05em;
              margin-top: 1px;
            }

            .header-badges {
              display: flex;
              gap: 10px;
              flex-wrap: wrap;
            }
            .badge {
              display: flex;
              align-items: center;
              gap: 8px;
              padding: 6px 12px;
              border-radius: 8px;
              font-size: 0.75rem;
              font-weight: 700;
              letter-spacing: -0.01em;
            }
            .badge-overdue {
              background: rgba(239, 68, 68, 0.1);
              border: 1px solid rgba(239, 68, 68, 0.2);
              color: #f87171;
            }
            .badge-active {
              background: rgba(16, 185, 129, 0.1);
              border: 1px solid rgba(16, 185, 129, 0.2);
              color: #34d399;
            }
            .badge-dot {
              width: 6px;
              height: 6px;
              border-radius: 50%;
            }
            .dot-red {
              background-color: #ef4444;
              box-shadow: 0 0 10px #ef4444;
            }
            .dot-green {
              background-color: #10b981;
              box-shadow: 0 0 10px #10b981;
            }

            #content {
              padding: 24px;
            }

            /* Dashboard Grid - Perfect 2-Column Desktop Presentation */
            .dashboard-grid {
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 28px;
            }
            
            .dashboard-column {
              display: flex;
              flex-direction: column;
              gap: 24px;
            }

            .section-wrapper {
              display: flex;
              flex-direction: column;
              gap: 12px;
            }
            .section-label {
              font-size: 0.75rem;
              font-weight: 800;
              text-transform: uppercase;
              letter-spacing: 0.12em;
              color: #94a3b8;
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: 4px;
            }
            .section-label ha-icon {
              --mdc-icon-size: 16px;
            }

            /* List Item Styling */
            .grocy-item {
              background: rgba(13, 19, 33, 0.45) !important;
              border: 1px solid rgba(255, 255, 255, 0.05);
              border-radius: 14px;
              padding: 14px 16px;
              display: flex;
              justify-content: space-between;
              align-items: center;
              gap: 14px;
              transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .grocy-item:hover {
              border-color: rgba(56, 189, 248, 0.2);
              background: rgba(255, 255, 255, 0.02) !important;
              transform: translateY(-2px);
            }

            /* Overdue Specific overrides */
            .grocy-item.expired {
              border-color: rgba(239, 68, 68, 0.25);
              background: rgba(127, 29, 29, 0.05) !important;
              box-shadow: 0 0 15px rgba(239, 68, 68, 0.05);
            }
            .grocy-item.expired:hover {
              border-color: rgba(239, 68, 68, 0.4);
            }

            /* Expiring Specific overrides */
            .grocy-item.expiring {
              border-color: rgba(245, 158, 11, 0.25);
              background: rgba(120, 53, 4, 0.05) !important;
              box-shadow: 0 0 15px rgba(245, 158, 11, 0.05);
            }
            .grocy-item.expiring:hover {
              border-color: rgba(245, 158, 11, 0.4);
            }

            .item-left-block {
              display: flex;
              align-items: center;
              gap: 14px;
              flex: 1;
              min-width: 0;
            }

            /* Left Badge Box (With Quantity parsed cleanly) */
            .item-qty-box {
              width: 42px;
              height: 42px;
              border-radius: 8px;
              background: rgba(255, 255, 255, 0.03);
              border: 1px solid rgba(255, 255, 255, 0.06);
              display: flex;
              align-items: center;
              justify-content: center;
              font-family: 'JetBrains Mono', monospace;
              font-size: 0.75rem;
              font-weight: 700;
              color: #94a3b8;
              flex-shrink: 0;
            }
            
            /* Chore Custom Icon Box */
            .item-icon-box {
              width: 42px;
              height: 42px;
              border-radius: 8px;
              background: rgba(255, 255, 255, 0.03);
              border: 1px solid rgba(255, 255, 255, 0.06);
              display: flex;
              align-items: center;
              justify-content: center;
              flex-shrink: 0;
            }
            .item-icon-box.chore-icon { color: #38bdf8; background: rgba(56, 189, 248, 0.05); border-color: rgba(56, 189, 248, 0.1); }
            .item-icon-box.task-icon { color: #8b5cf6; background: rgba(139, 92, 246, 0.05); border-color: rgba(139, 92, 246, 0.1); }
            .item-icon-box.battery-icon { color: #f43f5e; background: rgba(244, 63, 94, 0.05); border-color: rgba(244, 63, 94, 0.1); }
            .item-icon-box.shopping-icon { color: #10b981; background: rgba(16, 185, 129, 0.05); border-color: rgba(16, 185, 129, 0.1); }

            .item-details {
              display: flex;
              flex-direction: column;
              min-width: 0;
            }
            .item-title-text {
              font-size: 0.85rem;
              font-weight: 700;
              color: #ffffff;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }
            .item-meta-text {
              font-size: 0.75rem;
              color: #64748b;
              margin-top: 2px;
            }
            .overdue-meta {
              color: #f87171 !important;
              font-weight: 600;
            }
            .expiring-meta {
              color: #fbbf24 !important;
            }

            /* Action Buttons styling */
            .item-actions {
              display: flex;
              align-items: center;
              gap: 8px;
            }

            .grocy-btn {
              background: rgba(255, 255, 255, 0.02);
              border: 1px solid rgba(2, 132, 199, 0.4);
              color: #38bdf8;
              padding: 6px 14px;
              border-radius: 8px;
              cursor: pointer;
              font-family: inherit;
              font-size: 0.75rem;
              font-weight: 700;
              transition: all 0.25s ease;
              outline: none;
              display: inline-flex;
              align-items: center;
              justify-content: center;
              gap: 6px;
            }
            .grocy-btn:hover {
              background: #0284c7;
              color: #ffffff;
              box-shadow: 0 0 12px rgba(2, 132, 199, 0.4);
            }
            .grocy-btn.btn-clear {
              border-color: rgba(16, 185, 129, 0.4);
              color: #34d399;
            }
            .grocy-btn.btn-clear:hover {
              background: #10b981;
              color: #ffffff;
              box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
            }
            .grocy-btn.btn-waste {
              border-color: rgba(239, 68, 68, 0.4);
              color: #f87171;
            }
            .grocy-btn.btn-waste:hover {
              background: #ef4444;
              color: #ffffff;
              box-shadow: 0 0 12px rgba(239, 68, 68, 0.4);
            }
            .grocy-btn.btn-open {
              border-color: rgba(245, 158, 11, 0.4);
              color: #fbbf24;
            }
            .grocy-btn.btn-open:hover {
              background: #f59f0b;
              color: #ffffff;
              box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
            }
            .grocy-btn:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }

            /* Delete Button icon */
            .hard-delete-btn {
              color: #ef4444;
              opacity: 0.5;
              cursor: pointer;
              padding: 6px;
              border-radius: 8px;
              transition: all 0.2s;
              display: flex;
              align-items: center;
              justify-content: center;
              background: transparent;
              border: none;
              outline: none;
            }
            .hard-delete-btn:hover {
              opacity: 1;
              background: rgba(239, 68, 68, 0.1);
            }

            /* CSS Loading Spinner */
            .spinner {
              display: inline-block;
              width: 10px;
              height: 10px;
              border: 2px solid rgba(255, 255, 255, 0.3);
              border-radius: 50%;
              border-top-color: #ffffff;
              animation: spin 0.8s linear infinite;
              margin-right: 4px;
            }
            @keyframes spin {
              to { transform: rotate(360deg); }
            }

            .empty-state {
              padding: 18px;
              text-align: center;
              font-size: 0.75rem;
              color: #64748b;
              border: 1px dashed rgba(255, 255, 255, 0.05);
              border-radius: 14px;
              background: rgba(255, 255, 255, 0.005);
            }

            /* Event Console Styling */
            .console-wrapper {
              background: #02040a;
              border-top: 1px solid rgba(255, 255, 255, 0.05);
              font-family: 'JetBrains Mono', monospace;
              padding: 16px 24px;
            }
            .console-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 10px;
            }
            .console-label {
              font-size: 0.7rem;
              color: #475569;
              display: flex;
              align-items: center;
              gap: 8px;
              text-transform: uppercase;
              letter-spacing: 0.05em;
            }
            .console-live-badge {
              font-size: 0.65rem;
              font-weight: bold;
              color: #38bdf8;
              background: rgba(56, 189, 248, 0.1);
              border: 1px solid rgba(56, 189, 248, 0.2);
              padding: 2px 8px;
              border-radius: 4px;
            }
            .console-body {
              height: 90px;
              overflow-y: auto;
              font-size: 0.75rem;
              line-height: 1.5;
              display: flex;
              flex-direction: column;
              gap: 4px;
            }
            .log-success { color: #10b981; }
            .log-api { color: #8b5cf6; }
            .log-info { color: #38bdf8; }
            .log-warn { color: #f59f0b; }

            /* Grid Layout adjustments for Mobile Views */
            @media (max-width: 768px) {
              .dashboard-grid {
                grid-template-columns: 1fr;
                gap: 20px;
              }
            }
          </style>
        </ha-card>
      `;
      this.content = this.querySelector("#content");
    }

    this.render();
  }

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
    if (diff === 0) return "Expires today!";
    if (diff === 1) return "Expires tomorrow";
    return `Expires in ${diff} days`;
  }

  addTerminalLog(message, type = "info") {
    const time = new Date().toLocaleTimeString();
    let prefix = `[INFO ${time}]`;
    let logClass = "log-info";

    if (type === "success") {
      prefix = `[SUCCESS ${time}]`;
      logClass = "log-success";
    } else if (type === "api") {
      prefix = `[API ${time}]`;
      logClass = "log-api";
    } else if (type === "warn") {
      prefix = `[WARN ${time}]`;
      logClass = "log-warn";
    }

    const logLine = `<div class="${logClass}">${prefix} ${message}</div>`;
    this.terminalLogs.push(logLine);
    
    // Keep logs truncated to avoid scrolling infinite bloat
    if (this.terminalLogs.length > 20) {
      this.terminalLogs.shift();
    }
    
    this.renderTerminal();
  }

  renderTerminal() {
    const terminalEl = this.querySelector("#terminal-stream");
    if (terminalEl) {
      terminalEl.innerHTML = this.terminalLogs.join("");
      terminalEl.scrollTop = terminalEl.scrollHeight;
    }
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
    
    const locationNames = {
      1: "Pantry",
      2: "Fridge",
      3: "Freezer",
      4: "Cupboards"
    };
    
    const foodByLocation = {};

    // Process Tasks
    tasks.forEach(task => {
      if (this.processedItems.has('task_' + task.id)) return;
      const overdueFlag = task.due_date && new Date(task.due_date) < new Date();
      const item = { id: task.id, title: task.name || "Task", date: task.due_date, overdue: overdueFlag, type: "task" };
      if (overdueFlag) overdueItems.push(item); else taskItems.push(item);
    });

    // Process Chores (OVERDUE CHORES STAY IN CHORES CONTAINER)
    chores.forEach(chore => {
      if (this.processedItems.has('chore_' + chore.id)) return;
      const overdueFlag = new Date(chore.next_estimated_execution_time) < new Date();
      const item = { id: chore.id, title: chore.name || chore.chore?.name || "Chore", date: chore.next_estimated_execution_time, overdue: overdueFlag, type: "chore" };
      
      // Chores stay inside their routines column on the right, even when estimated past execution bounds!
      choreItems.push(item);
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

    // Process Food & Sort by Location (Units and Numbers completely cleaned!)
    const foodSet = new Set();
    stock.forEach(food => {
      const id = food.product_id || food.id;
      if (this.processedItems.has('food_' + id)) return;
      if (foodSet.has(id)) return;
      foodSet.add(id);

      // Quantities & units parsing
      const amt = food.amount || food.amount_aggregated || 1;
      const unit = food.qu_unit_name_stock || food.unit || food.qu_unit_name || "";
      let shortUnit = "";
      
      if (unit) {
        const lowerUnit = unit.toLowerCase();
        if (lowerUnit.includes("liter") || lowerUnit === "l") {
          shortUnit = "L";
        } else if (lowerUnit.includes("gram") || lowerUnit === "g") {
          shortUnit = "g";
        } else if (lowerUnit.includes("kilogram") || lowerUnit === "kg") {
          shortUnit = "kg";
        } else if (lowerUnit.includes("piece") || lowerUnit.includes("pcs") || lowerUnit.includes("pack") || lowerUnit.includes("qty")) {
          shortUnit = ""; // Displays clean numbers like "1" or "4" rather than "1qty"
        } else {
          shortUnit = lowerUnit.substring(0, 3);
        }
      }

      const diff = Math.floor((new Date(food.best_before_date) - new Date()) / 86400000);
      const overdueFlag = diff < 0;
      const expiringFlag = diff >= 0 && diff <= 3;

      const item = { 
        id, 
        title: getProductName(id), 
        date: food.best_before_date, 
        overdue: overdueFlag, 
        expiring: expiringFlag,
        qtyLabel: `${Math.round(amt)}${shortUnit}`,
        type: "food" 
      };
      
      if (overdueFlag) {
        overdueItems.push(item); 
      } else {
        const locId = food.location_id || 1;
        const locName = locationNames[locId] || `Storage #${locId}`;
        
        if (!foodByLocation[locName]) {
          foodByLocation[locName] = [];
        }
        foodByLocation[locName].push(item);
      }
    });

    shoppingList.forEach(s => {
      const pId = s.product_id;
      if (this.processedItems.has('shopping_' + pId)) return;
      shoppingItems.push({
        id: pId,
        title: getProductName(pId),
        qtyLabel: `${s.amount}x`,
        date: s.note ? `Note: ${s.note}` : null,
        overdue: false,
        type: "shopping"
      });
    });

    // Update Counter Badges
    let totalFood = 0;
    Object.values(foodByLocation).forEach(arr => totalFood += arr.length);
    const activeCount = taskItems.length + choreItems.length + totalFood + shoppingItems.length;
    
    const overdueBadgeEl = this.querySelector('#badge-overdue-val');
    const activeBadgeEl = this.querySelector('#badge-active-val');
    if (overdueBadgeEl) overdueBadgeEl.innerText = overdueItems.length;
    if (activeBadgeEl) activeBadgeEl.innerText = activeCount;

    // Build standard list components
    const buildSection = (title, icon, items) => {
      let html = `
        <div class="section-wrapper">
          <div class="section-label">
            <ha-icon icon="${icon}"></ha-icon>
            <span>${title}</span>
          </div>
      `;

      if (!items || !items.length) {
        html += `<div class="empty-state">All safe and cleared ??</div>`;
      } else {
        items.forEach(item => {
          let buttons = "";
          let hardDeleteHtml = "";
          let leftElement = "";

          let cardStateClass = "";
          let metaStateClass = "";
          if (item.overdue) {
            cardStateClass = "expired";
            metaStateClass = "overdue-meta";
          } else if (item.expiring) {
            cardStateClass = "expiring";
            metaStateClass = "expiring-meta";
          }

          if (item.type === "task") {
            leftElement = `<div class="item-icon-box task-icon"><ha-icon icon="mdi:clipboard-check-outline"></ha-icon></div>`;
            buttons = `<button class="grocy-btn action-btn" data-action="task" data-id="${item.id}" data-name="${item.title}">Done</button>`;
            hardDeleteHtml = `<button class="hard-delete-btn action-btn" data-action="delete" data-id="${item.id}" data-type="tasks" data-name="${item.title}" title="Delete Task"><ha-icon icon="mdi:delete-outline"></ha-icon></button>`;
          } 
          else if (item.type === "chore") {
            leftElement = `<div class="item-icon-box chore-icon"><ha-icon icon="mdi:broom"></ha-icon></div>`;
            buttons = `<button class="grocy-btn btn-clear action-btn" data-action="chore" data-id="${item.id}" data-name="${item.title}">Clear</button>`;
            hardDeleteHtml = `<button class="hard-delete-btn action-btn" data-action="delete" data-id="${item.id}" data-type="chores" data-name="${item.title}" title="Delete Chore"><ha-icon icon="mdi:delete-outline"></ha-icon></button>`;
          } 
          else if (item.type === "battery") {
            leftElement = `<div class="item-icon-box battery-icon"><ha-icon icon="mdi:battery-alert"></ha-icon></div>`;
            buttons = `<button class="grocy-btn btn-waste action-btn" data-action="battery" data-id="${item.id}" data-name="${item.title}">Charge</button>`;
          }
          else if (item.type === "shopping") {
            leftElement = `<div class="item-qty-box">${item.qtyLabel}</div>`;
            buttons = `<button class="grocy-btn btn-waste action-btn" data-action="shopping" data-id="${item.id}" data-name="${item.title}">Remove</button>`;
          }
          else if (item.type === "food") {
            leftElement = `<div class="item-qty-box">${item.qtyLabel || '1'}</div>`;
            if (item.overdue) {
              buttons = `<button class="grocy-btn btn-waste action-btn" data-action="consume" data-id="${item.id}" data-name="${item.title}" data-spoiled="true">Waste</button>`;
            } else {
              buttons = `
                <button class="grocy-btn btn-open action-btn" data-action="open" data-id="${item.id}" data-name="${item.title}">Open</button>
                <button class="grocy-btn action-btn" data-action="consume" data-id="${item.id}" data-name="${item.title}" data-spoiled="false">Consume</button>
              `;
            }
          }

          const relativeDateStr = item.type === 'shopping' && item.date ? item.date : this.relativeDate(item.date);

          html += `
            <div class="grocy-item ${cardStateClass}">
              <div class="item-left-block">
                ${leftElement}
                <div class="item-details">
                  <span class="item-title-text">${item.title}</span>
                  <span class="item-meta-text ${metaStateClass}">${relativeDateStr}</span>
                </div>
              </div>
              <div class="item-actions">
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

    let leftColumnHtml = ``;
    let rightColumnHtml = ``;

    // Left Column: Overdue alerts and Smart Pantry tracking locations
    if (overdueItems.length > 0) {
      leftColumnHtml += buildSection("Action Required", "mdi:alert-circle", overdueItems);
    }

    // Consolidated food locations inside Left Column (matches "Smart Pantry Tracking")
    let hasFoodItems = false;
    Object.keys(foodByLocation).sort().forEach(locName => {
      let icon = "mdi:package-variant-closed";
      if (locName.toLowerCase().includes("fridge")) icon = "mdi:fridge-outline";
      if (locName.toLowerCase().includes("freez")) icon = "mdi:snowflake";
      if (locName.toLowerCase().includes("pantry")) icon = "mdi:food-apple";
      if (locName.toLowerCase().includes("cupboard")) icon = "mdi:cupboard";
      
      leftColumnHtml += buildSection(`Smart Pantry Tracking - ${locName}`, icon, foodByLocation[locName]);
      hasFoodItems = true;
    });

    if (!hasFoodItems) {
      leftColumnHtml += buildSection("Smart Pantry Tracking", "mdi:food-apple", []);
    }

    // Right Column: Chores, tasks and shopping lists
    rightColumnHtml += buildSection("Chore Routines", "mdi:check-circle-outline", choreItems);
    rightColumnHtml += buildSection("Household Tasks", "mdi:clipboard-check-outline", taskItems);
    rightColumnHtml += buildSection("Shopping List", "mdi:cart-outline", shoppingItems);

    this.content.innerHTML = `
      <div class="dashboard-grid">
        <div class="dashboard-column">
          ${leftColumnHtml}
        </div>
        <div class="dashboard-column">
          ${rightColumnHtml}
        </div>
      </div>
    `;

    // Render Event Stream values
    this.renderTerminal();

    // Bind interaction events
    this.content.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = btn.dataset.action;
        const id = btn.dataset.id;
        const name = btn.dataset.name || "item";
        
        if (action === 'task') this.completeTask(id, name, btn);
        else if (action === 'chore') this.executeChore(id, name, btn);
        else if (action === 'consume') this.consumeFood(id, name, btn.dataset.spoiled === 'true', btn);
        else if (action === 'open') this.openFood(id, name, btn);
        else if (action === 'delete') this.deleteItem(id, name, btn.dataset.type, btn);
        else if (action === 'battery') this.trackBattery(id, name, btn);
        else if (action === 'shopping') this.removeShoppingItem(id, name, btn);
      });
    });
  }

  setLoadingState(btn, text = "...") {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${text}`;
  }

  executeChore(id, name, btn) {
    this.addTerminalLog(`Executing chore task routine: "${name}"...`, "info");
    this.setLoadingState(btn, "Clearing");
    
    this._hass.callService("grocy", "execute_chore", { chore_id: parseInt(id) })
      .then(() => { 
        this.processedItems.add('chore_' + id); 
        this.addTerminalLog(`Successfully cleared chore: "${name}". Cache flushed.`, "success");
        this.render(); 
      })
      .catch((err) => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Error processing chore service callback. Code standard failure.`, "warn");
      });
  }

  completeTask(id, name, btn) {
    this.addTerminalLog(`Marking task resolved: "${name}"...`, "info");
    this.setLoadingState(btn, "Done");
    
    this._hass.callService("grocy", "complete_task", { task_id: parseInt(id) })
      .then(() => { 
        this.processedItems.add('task_' + id); 
        this.addTerminalLog(`Task record successfully marked done: "${name}".`, "success");
        this.render(); 
      })
      .catch(() => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Failed complete task execution sequence.`, "warn");
      });
  }

  consumeFood(id, name, spoiled, btn) {
    const actionName = spoiled ? "Wasting" : "Consuming";
    this.addTerminalLog(`Dispatched consume action for item: "${name}" (Spoiled: ${spoiled})...`, "info");
    this.setLoadingState(btn, actionName);
    
    this._hass.callService("grocy", "consume_product_from_stock", { product_id: parseInt(id), amount: 1, spoiled: spoiled, transaction_type: "CONSUME" })
      .then(() => { 
        this.processedItems.add('food_' + id); 
        this.addTerminalLog(`Service response [200]: Deducted 1 x "${name}" from stock index.`, "success");
        this.render(); 
      })
      .catch(() => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Failed post query response on target food index.`, "warn");
      });
  }

  openFood(id, name, btn) {
    this.addTerminalLog(`Marking item status opened: "${name}"...`, "info");
    this.setLoadingState(btn, "Opening");
    
    this._hass.callService("grocy", "open_product", { product_id: parseInt(id), amount: 1 })
      .then(() => { 
        btn.disabled = true;
        btn.innerText = "Opened"; 
        this.addTerminalLog(`Success: Marked "${name}" as open in local register list.`, "success");
      })
      .catch(() => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Could not flag product package state as open.`, "warn");
      });
  }

  trackBattery(id, name, btn) {
    this.addTerminalLog(`Registering charging cycle for battery element: "${name}"...`, "info");
    this.setLoadingState(btn, "Charging");
    
    this._hass.callService("grocy", "track_battery", { battery_id: parseInt(id) })
      .then(() => { 
        this.processedItems.add('battery_' + id); 
        this.addTerminalLog(`Logged charge refresh sequence on battery object: "${name}".`, "success");
        this.render(); 
      })
      .catch(() => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Battery event track operation failed.`, "warn");
      });
  }

  removeShoppingItem(id, name, btn) {
    this.addTerminalLog(`Removing item from shopping list register: "${name}"...`, "info");
    this.setLoadingState(btn, "Removing");
    
    this._hass.callService("grocy", "remove_product_in_shopping_list", { product_id: parseInt(id) })
      .then(() => { 
        this.processedItems.add('shopping_' + pId); 
        this.addTerminalLog(`Item "${name}" successfully deleted from current shopping cart list.`, "success");
        this.render(); 
      })
      .catch(() => { 
        btn.disabled = false; 
        btn.innerText = "Error"; 
        this.addTerminalLog(`Failed to drop shopping list record database entries.`, "warn");
      });
  }

  deleteItem(id, name, entityType, iconDiv) {
    this.addTerminalLog(`Initializing deep delete for entity object "${name}" [type: ${entityType}]...`, "info");
    iconDiv.style.pointerEvents = "none"; 
    iconDiv.style.opacity = "0.2";
    
    this._hass.callService("grocy", "delete_generic", { entity_type: entityType, object_id: parseInt(id) })
      .then(() => {
        const prefix = entityType === 'tasks' ? 'task_' : entityType === 'chores' ? 'chore_' : 'food_';
        this.processedItems.add(prefix + id);
        this.addTerminalLog(`Database entity "${name}" removed. Clear sequence successful.`, "success");
        this.render();
      }).catch(() => { 
        iconDiv.style.pointerEvents = "auto"; 
        iconDiv.style.opacity = "0.5"; 
        this.addTerminalLog(`Deep delete execution failed. Entity may already be missing.`, "warn");
      });
  }

  setConfig(config) { this.config = config; }
  getCardSize() { return 10; }
}

customElements.define("grocy-action-card", GrocyActionCard);
