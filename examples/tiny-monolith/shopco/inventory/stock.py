"""Inventory reaches back into orders: this closes a dependency cycle."""
import shopco.orders.service as orders_service
from shopco.audit.log import record

STOCK = {"BOOK-1": 10, "BOOK-2": 3}


def reserve(sku, quantity):
    if STOCK.get(sku, 0) < quantity:
        raise ValueError("out of stock")
    STOCK[sku] -= quantity
    record("stock.reserved", {"sku": sku, "quantity": quantity})


def pending_demand(sku):
    return sum(o["quantity"] for o in orders_service.open_orders_for(sku))
