"""Third-party code bundled with Grocy Pro.

`grocy/` is grocy-py 1.3.0 (MIT, https://github.com/iamkarlson/grocy-py; license
in grocy/LICENSE), unchanged
apart from this location. It is bundled instead of installed because grocy-py
owns the top-level `grocy` module: the old Grocy integration (domain `grocy`)
pins grocy-py 0.1.0, Home Assistant switches the installed version back and
forth between the two pins, and the first one imported stays in memory. With
its own copy Grocy Pro always runs the version it was tested with, next to the
old integration or without it.

Update: copy the new release's `grocy/` package here and bump GROCY_PY_VERSION.
"""

GROCY_PY_VERSION = "1.3.0"
