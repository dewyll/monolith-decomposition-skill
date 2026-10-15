"""Entry point. Lives in the root namespace on purpose (an orphan)."""
from shopco.orders.service import place_order
from shopco.reporting.sales import daily_report


def main():
    order = place_order(customer_id=1, sku="BOOK-1", quantity=2)
    print(order)
    print(daily_report())


if __name__ == "__main__":
    main()
