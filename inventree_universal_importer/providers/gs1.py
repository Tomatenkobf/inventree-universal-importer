"""GS1 is an extension point, not an invented universal API.

Implement a Provider subclass for the contracted GS1 member-organisation API
and register it. See docs/providers.md. No requests are sent by this module.
"""

AVAILABILITY = (
    "Unavailable: a specific GS1 API contract and documentation are required."
)
