from decimal import Decimal


def format_quantity(quantity):
    """Render a Decimal like 500.00 as '500' and 0.50 as '0.5'."""
    if quantity is None:
        return ""
    text = f"{Decimal(quantity):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text
