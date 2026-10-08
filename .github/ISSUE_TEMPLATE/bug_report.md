---
name: 🐛 Bug report
about: Report a problem or unexpected behavior in Grocy Pro
title: "[BUG] <Brief description of the issue>"
labels: bug
assignees: ''
---

## 🛑 Checklist
- [ ] I am using the latest version of Grocy Pro.
- [ ] I have checked the existing open and closed issues.
- [ ] I have enabled debug logging and included the logs below.

## 📝 Describe the bug
A clear and concise description of what the bug is.

## ⚙️ Environment
- **Home Assistant version:** (e.g. 2026.10.1)
- **Grocy Pro version:** (e.g. v3.0.0)
- **Grocy version:** (Grocy → About, e.g. 4.7.1)
- **How Grocy runs:** (HA add-on / Docker / other, behind a reverse proxy?)
- **Installation method:** (HACS / manual)
- **Migrated from the old `grocy` integration:** (Yes / No)

## 🔄 To reproduce
1. Go to '...'
2. Call action '...'
3. See error

## 🎯 Expected behavior

## 💥 Actual behavior

## 📋 Logs
Settings → System → Logs. To enable debug logging, add this to `configuration.yaml`, restart and trigger the issue again:

```yaml
logger:
  default: info
  logs:
    custom_components.grocy_pro: debug
    grocy: debug
```

Or download the diagnostics: Settings → Devices & services → Grocy Pro → ⋮ → Download diagnostics (the API key and URL are redacted).
