"""
Example: Using get_active_order_lines_for_scheduling() for Production Scheduling

This example demonstrates how to retrieve order data for scheduling purposes,
with support for aggregating quantities when multiple order lines exist for
the same product + due date combination.
"""

from datetime import date, timedelta
from orders.core.services.csv_import import CSVImportService


def example_aggregated_scheduling():
    """
    Example: Get aggregated order data for scheduling

    Use case: When scheduling production, you need total quantities by
    product + due date, but don't need individual order numbers.
    """
    print("=== Aggregated Order Data for Scheduling ===\n")

    # Get aggregated data (default behavior)
    aggregated_data = CSVImportService.get_active_order_lines_for_scheduling(
        aggregate=True  # This is the default
    )

    print("Total records:", aggregated_data.count())
    print("\nSample aggregated data:\n")

    for item in aggregated_data[:10]:  # Show first 10 records
        print(f"Customer: {item['customer_code']}")
        print(f"  Product: {item['product_code']}")
        print(f"  Due Date: {item['due_date']}")
        print(f"  Total Quantity: {item['total_quantity']}")
        print(f"  Order Type: {item['order_type']}")
        print(f"  Line Count: {item['line_count']} (individual order lines aggregated)")
        print()

    return aggregated_data


def example_individual_order_lines():
    """
    Example: Get individual order line details

    Use case: When you need to see all individual order numbers and line details
    for reference or reporting purposes.
    """
    print("=== Individual Order Line Details ===\n")

    # Get individual order lines
    individual_lines = CSVImportService.get_active_order_lines_for_scheduling(
        aggregate=False
    )

    print("Total order lines:", individual_lines.count())
    print("\nSample individual lines:\n")

    for line in individual_lines[:10]:  # Show first 10 records
        print(f"Order: {line.order.order_no}")
        print(f"  Line No: {line.line_no}")
        print(f"  Customer: {line.order.customer.customer_code}")
        print(f"  Product: {line.product_code}")
        print(f"  Due Date: {line.due_date}")
        print(f"  Quantity: {line.quantity}")
        print(f"  Order Type: {line.order.order_type}")
        print()

    return individual_lines


def example_filtered_scheduling():
    """
    Example: Get aggregated data with filters

    Use case: Schedule production for a specific customer, product, and date range
    """
    print("=== Filtered Aggregated Data ===\n")

    # Example: Get data for customer 000001 (Tiera) for next 30 days
    today = date.today()
    end_date = today + timedelta(days=30)

    aggregated_data = CSVImportService.get_active_order_lines_for_scheduling(
        customer_id=1,  # Assuming customer ID 1 is Tiera
        start_date=today,
        end_date=end_date,
        aggregate=True
    )

    print(f"Records for next 30 days: {aggregated_data.count()}\n")

    for item in aggregated_data:
        print(f"{item['due_date']}: {item['product_code']} x {item['total_quantity']} ({item['order_type']})")

    return aggregated_data


def example_handling_duplicates():
    """
    Example: Demonstrating how duplicates are handled

    Scenario: Same product + due date appears in 10+ different order numbers
    (as seen in ティエラ_確定.csv)
    """
    print("=== Handling Multiple Order Lines for Same Product + Date ===\n")

    # Get aggregated data
    aggregated = CSVImportService.get_active_order_lines_for_scheduling(
        product_code='24201-36010',  # Example product from CSV
        aggregate=True
    )

    for item in aggregated:
        if item['line_count'] > 1:
            print(f"Product: {item['product_code']}")
            print(f"Due Date: {item['due_date']}")
            print(f"Total Quantity: {item['total_quantity']}")
            print(f"Aggregated from {item['line_count']} individual order lines")
            print()

    # If you need to see the individual order numbers:
    print("To see individual order numbers, use aggregate=False:\n")

    individual = CSVImportService.get_active_order_lines_for_scheduling(
        product_code='24201-36010',
        aggregate=False
    )

    for line in individual:
        print(f"  Order: {line.order.order_no}, Line: {line.line_no}, Qty: {line.quantity}")


def example_priority_handling():
    """
    Example: Understanding FIRM vs FORECAST priority

    The method returns both FIRM and FORECAST orders.
    Scheduling logic should prioritize FIRM orders.
    """
    print("=== Priority Handling: FIRM vs FORECAST ===\n")

    aggregated = CSVImportService.get_active_order_lines_for_scheduling(
        aggregate=True
    )

    # Group by order_type
    firm_orders = [item for item in aggregated if item['order_type'] == 'FIRM']
    forecast_orders = [item for item in aggregated if item['order_type'] == 'FORECAST']

    print(f"FIRM orders: {len(firm_orders)}")
    print(f"FORECAST orders: {len(forecast_orders)}")
    print()
    print("Note: When FIRM and FORECAST exist for same product + date,")
    print("      FIRM should be used for scheduling, FORECAST ignored.")
    print("      This logic should be implemented in the scheduling engine.")


# ============================================================================
# SQL Query Generated by Django ORM (for reference)
# ============================================================================
"""
When aggregate=True, Django generates SQL similar to:

SELECT
    t_order.customer_id,
    m_customer.customer_code,
    t_order_line.product_code,
    t_order_line.due_date,
    t_order.order_type,
    SUM(t_order_line.quantity) as total_quantity,
    COUNT(t_order_line.id) as line_count
FROM t_order_line
INNER JOIN t_order ON t_order_line.order_id = t_order.id
INNER JOIN m_customer ON t_order.customer_id = m_customer.id
WHERE t_order.status = 'OPEN'
GROUP BY
    t_order.customer_id,
    m_customer.customer_code,
    t_order_line.product_code,
    t_order_line.due_date,
    t_order.order_type
ORDER BY
    t_order_line.due_date,
    t_order.order_type,
    t_order_line.product_code;
"""


if __name__ == '__main__':
    print("This is an example file. Run these functions in Django shell:\n")
    print("from production.services.scheduling_example import *")
    print("example_aggregated_scheduling()")
    print("example_individual_order_lines()")
    print("example_filtered_scheduling()")
    print("example_handling_duplicates()")
    print("example_priority_handling()")
