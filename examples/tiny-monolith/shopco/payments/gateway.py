from shopco.audit.log import record
from shopco.notification.email import send_email


def charge(customer, amount):
    record("payment.charged", {"customer": customer["id"], "amount": amount})
    send_email(customer["email"], f"We charged {amount}")
    return {"status": "ok", "amount": amount}


def refund(customer, amount):
    record("payment.refunded", {"customer": customer["id"], "amount": amount})
    return {"status": "ok", "amount": -amount}
