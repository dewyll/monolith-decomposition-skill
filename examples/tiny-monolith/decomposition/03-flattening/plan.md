# Flattening plan

| Component | Orphan files | Option | Target | RFC |
|---|---|---|---|---|
| `shopco.orders` | `shopco/orders/__init__.py`, `shopco/orders/service.py` | push down | `shopco.orders.core` | 0004 |
| `shopco` | `shopco/__init__.py`, `shopco/app.py` | keep (entry point) | — | 0004 |

The moves run as the first step of the ordering-service extraction. After
them, re-measure into this folder (`size_components.py --out-dir 03-flattening`),
delete the two allow-list entries that point to RFC-0004 and to RFC-0002, and
check that F1.2 and F3.1 still pass.
