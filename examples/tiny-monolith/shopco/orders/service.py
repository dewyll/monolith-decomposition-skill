"""Orders: code sitting next to the `pricing` sub-package (root-with-code)."""
from shopco.orders.pricing.calculator import price_for
from shopco.inventory.stock import reserve
from shopco.notification.email import send_email
from shopco.audit.log import record
from shopco.customers.profile import get_customer

ORDERS = []


def place_order(customer_id, sku, quantity):
    customer = get_customer(customer_id)
    reserve(sku, quantity)
    total = price_for(sku, quantity, customer["tier"])
    order = {"id": len(ORDERS) + 1, "customer": customer_id, "sku": sku,
             "quantity": quantity, "total": total, "status": "placed"}
    ORDERS.append(order)
    record("order.placed", order)
    send_email(customer["email"], f"Order {order['id']} placed")
    return order


def cancel_order(order_id):
    for order in ORDERS:
        if order["id"] == order_id:
            order["status"] = "cancelled"
            record("order.cancelled", order)
            return order
    return None


def open_orders_for(sku):
    return [o for o in ORDERS if o["sku"] == sku and o["status"] == "placed"]
