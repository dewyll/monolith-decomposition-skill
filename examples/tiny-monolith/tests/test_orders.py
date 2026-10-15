from shopco.orders.service import place_order


def test_place_order():
    assert place_order(1, "BOOK-1", 1)["status"] == "placed"
