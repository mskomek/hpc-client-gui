# UI Framework Boundary

The services layer owns state, decisions, and toolkit-neutral view models.
Qt and a future wx adapter own widgets, timers, focus, rendering, and native
dialog execution. Controllers publish data or request objects; adapters decide
how those requests look in the active toolkit.

`EventBus` stores weak callback references, so a destroyed view is not retained
by a controller. Adapters should unsubscribe explicitly when their lifecycle
ends, while dead callbacks are also removed during publication.

This documents the product contract, not a requirement to remove the current
Qt implementation. Native Qt behavior remains the compatibility baseline until
a wx adapter is introduced.
