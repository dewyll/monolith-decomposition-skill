CUSTOMERS = {1: {"id": 1, "email": "ana@example.com", "tier": "gold"},
             2: {"id": 2, "email": "bruno@example.com", "tier": "standard"}}


def get_customer(customer_id):
    return CUSTOMERS[customer_id]
