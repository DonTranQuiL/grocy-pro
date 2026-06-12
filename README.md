<div align="center">

<!-- Replace the src link below with a screenshot of your beautiful Grocy Command Center -->
<img width="auto" height="auto" alt="Grocy Overhaul Banner" src="https://github.com/user-attachments/assets/d0649f38-c73f-466c-bf3b-73bf9765febf" />


# 🛒 Grocy: The God-Tier Overhaul!
**The ultimate, zero-latency, AI-powered inventory engine and interactive Command Center dashboard for Home Assistant.**

> ⚠️ **MASSIVE OVERHAUL ANNOUNCEMENT (V2.0.0):** 
> We have taken the original Grocy integration and completely rebuilt the interaction layer! This repository provides a **Bulletproof Python Backend** (fixing legacy crash loops and executor bugs) paired natively with a brand-new **Optimistic UI Frontend Card**. Welcome to the era of instant clicks, NFC Smart Pantries, and AI Receipt Scanning!

[![Latest Release](https://img.shields.io/github/v/release/DonTranQuiL/grocy-pro?style=for-the-badge&color=007ec6)](https://github.com/DonTranQuiL/grocy-pro/releases)
[![License](https://img.shields.io/github/license/DonTranQuiL/grocy-pro?style=for-the-badge&color=007ec6)](https://github.com/DonTranQuiL/grocy-pro/blob/main/LICENSE)
[![Home Assistant CI](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/grocy-pro/hass-ci.yml?label=Home%20Assistant%20CI&style=for-the-badge)](https://github.com/DonTranQuiL/grocy-pro/actions/workflows/hass-ci.yml)
[![Code Checks](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/grocy-pro/codechecker.yml?style=for-the-badge&label=CODE%20CHECKS&color=5dbb0f)](https://github.com/DonTranQuiL/grocy-pro/actions)
[![Tests](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/grocy-pro/pytest.yml?style=for-the-badge&label=TESTS&color=5dbb0f)](https://github.com/DonTranQuiL/grocy-pro/actions)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/grocy-pro/hacs.yaml?style=for-the-badge&label=HACS%20VALIDATION&color=5dbb0f)](https://github.com/DonTranQuiL/grocy-pro/actions)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-5dbb0f?style=for-the-badge)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000?style=for-the-badge)](https://github.com/astral-sh/ruff)
[![HACS Custom](https://img.shields.io/badge/HACS-CUSTOM-ff6e27?style=for-the-badge)](https://hacs.xyz/)
[![Home Assistant Version](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-007ec6?style=for-the-badge)](https://www.home-assistant.io/)
[![Maintainer](https://img.shields.io/badge/maintainer-%40DonTranQuiL-007ec6?style=for-the-badge)](https://github.com/DonTranQuiL)
[![Donate](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-ffdd00?style=for-the-badge)](https://ko-fi.com/DonTranQuiL)
[![Community Forum](https://img.shields.io/badge/community-forum-007ec6?style=for-the-badge)](https://community.home-assistant.io/t/ads-b-tracker-for-home-assistant/1011081)

</div>

### 🚀 High-Performance Home Inventory Management
Stop digging through nested Home Assistant menus to check off your chores or throw away expired food. This overhauled integration pulls your entire household state—Food, Tasks, Chores, Shopping Lists, and Batteries—into a single, actionable ecosystem powered by a rock-solid Python backend and a beautifully designed, blazing-fast JavaScript frontend.

---

## 🌟 Core Features & Architecture

### ⚡ The "Optimistic UI" Engine (Grocy Command Center)
Standard Home Assistant dashboards suffer from "Polling Lag"—you click a button, the backend processes it, but the UI doesn't update for 30 seconds until the next polling cycle. 
Included in this repository is the **Grocy Command Center** custom Lovelace card. It utilizes a custom **Optimistic Execution Cache**. When you click "Done" on a chore or "Consume" on a food item, the card intercepts the action, fires the payload to the server, and **instantly hides the item from your screen**, adjusting your total counts in real-time. It feels like a blazing-fast native mobile app.

### 🛡️ Bulletproof Backend Architecture
The legacy Grocy integration suffered from aggressive polling crashes and `async_add_executor_job` keyword exceptions that would lock up the UI. We have rewritten the core execution handlers:
* **Zero-Crash Coordinators:** Missing entity arrays have been patched to ensure the Home Assistant data-loop never panics during rapid state changes.
* **Safe Service Wrappers:** All native Grocy API calls (`open_product`, `remove_product_in_shopping_list`) have been encapsulated in safe Python wrappers, completely eliminating `<Response [400]>` and `TabError` crashes.

### 🤖 AI Receipt Vision (The "Magic" Feature)
Nobody wants to manually type in 40 items after a grocery run. We have engineered a brand new service endpoint (`grocy.add_products_by_name`) that allows native LLMs (like Google Gemini 1.5 Flash or OpenAI) to restock your fridge automatically.
1. Tap the HA Assist microphone or snap a photo of your receipt.
2. The AI extracts the items, quantities, and prices.
3. The custom backend performs a fuzzy-search against your Grocy database, resolves the string names to exact `product_id` integers, and quietly stocks your digital fridge.

### 🏷️ Native NFC / RFID "Smart Pantry" Workflows
Turn your physical house into a smart database. Slap cheap NFC sticker tags on your dog food bin, coffee machine, or trash cans. Tap your phone to a bin and Home Assistant automatically triggers `grocy.consume_product_from_stock` and ticks off your daily chores.

### 🧹 Real-Time Zero-Bloat Entity Cleanup
The dashboard intelligently sorts your life into actionable lists:
* **Overdue/Action Required:** Items that need immediate attention (Red).
* **Pantry:** Food approaching its best-before date (Consume / Waste / Open).
* **Tasks & Chores:** Household management with 1-click completion.
* **Shopping Cart:** Direct integration to remove items as you walk through the supermarket aisles.

---

## 📥 Installation Guide

This God-Tier overhaul requires installing both the **Backend Integration** and the **Frontend Dashboard Card**.

### Part 1: Install the Backend (via HACS)
1. Open **HACS** in your sidebar and navigate into the **Integrations** panel.
2. Click the three dots (`...`) located in the upper right quadrant and select **Custom repositories**.
3. Input the repository web link: `https://github.com/DonTranQuiL/Grocy`
4. Set the Category selector dropdown to **Integration** and hit **Add**.
5. Locate the newly added **Grocy** repository card and hit **Download**.
6. ⚠️ **Restart your Home Assistant instance** to load the patched Python backend.

### Part 2: Install the Frontend (Grocy Command Center)
1. Inside this repository, locate the `grocy-action-card.js` file.
2. Copy this file into your Home Assistant `/config/www/` directory.
3. In Home Assistant, navigate to **Settings > Dashboards > Click the 3 dots in the top right > Resources**.
4. Click **Add Resource**.
5. Set the URL to `/local/grocy-action-card.js` and set the Resource Type to **JavaScript Module**.
6. Refresh your browser cache (`Ctrl + Shift + R`).

---

## 📍 Interactive Dashboard Configuration

To deploy the Command Center to your dashboard, simply use the visual editor, select "Manual Card", and paste the following YAML. *(Tip: Use the new 'Sections', 'Panel', or 'Sidebar' view layout in HA to let this card stretch out beautifully!)*

```yaml
type: custom:grocy-action-card
layout_options:
  grid_columns: 3
```

### Advanced UI Customization
The card dynamically adapts its Grid layout. If viewed on a narrow mobile phone, the buttons will safely wrap to prevent cut-offs. If viewed on a wide wall-mounted tablet, the statistics grid and action buttons expand horizontally to fill the space perfectly.

### 📱 Advanced Workflows & Automations
NFC "Smart Pantry" Template
Want to build an NFC tap-to-consume workflow? Use this native Home Assistant automation template to instantly execute multiple backend commands with a single physical tap:

```yaml
alias: "Grocy: NFC Tap - Feed the Dogs"
mode: single
trigger:
  - platform: tag
    tag_id: "YOUR_SCANNED_TAG_ID_HERE"
action:
  # Action 1: Consume 1 portion of Dog Food from Grocy
  - service: grocy.consume_product_from_stock
    data:
      product_id: 42 
      amount: 1
      transaction_type: CONSUME
      
  # Action 2: Check off the Morning Chore
  - service: grocy.execute_chore
    data:
      chore_id: 15
```

## AI Receipt Scanner Script
To utilize the AI Vision features, create this script in Home Assistant and pass an image helper to your AI model of choice:

```yaml
alias: "Grocy: Process Receipt with AI"
icon: mdi:receipt-text-scan
mode: single
sequence:
  - action: google_generative_ai_conversation.generate_content
    data:
      prompt: >
        Read this grocery receipt. Extract the items purchased, their quantities, and the prices. 
        Return ONLY a raw, valid JSON object matching this exact schema:
        {"items": [{"name": "Item Name", "amount": 1.0, "price": "2.99"}]}
        Do not include markdown blocks, backticks, or conversational text. Return ONLY the JSON.
      image_entity_id: image.receipt_scanner
    response_variable: ai_response
    
  - action: grocy.add_products_by_name
    data: "{{ ai_response.text | from_json }}"
```

### 🙏 Credits
Massive thanks to the developers of the original Home Assistant grocy-py custom component. This overhaul and frontend card was designed to patch, polish, and push their excellent initial API wrapper to the absolute limit of what is possible in Home Assistant.
