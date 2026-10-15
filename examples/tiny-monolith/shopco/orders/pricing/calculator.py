PRICES = {"BOOK-1": 30.0, "BOOK-2": 45.0}
DISCOUNT = {"gold": 0.1, "silver": 0.05}


def price_for(sku, quantity, tier="standard"):
    base = PRICES.get(sku, 0.0) * quantity
    return round(base * (1 - DISCOUNT.get(tier, 0.0)), 2)
