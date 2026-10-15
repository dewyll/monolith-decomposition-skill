"""Depends on nearly every other component."""
from shopco.orders.service import ORDERS
from shopco.inventory.stock import STOCK
from shopco.customers.profile import CUSTOMERS
from shopco.payments.gateway import charge
from shopco.audit.log import TRAIL


def daily_report():
    revenue = sum(o["total"] for o in ORDERS if o["status"] == "placed")
    return {"orders": len(ORDERS), "revenue": revenue, "stock": dict(STOCK),
            "customers": len(CUSTOMERS), "events": len(TRAIL), "charge_fn": charge.__name__}
