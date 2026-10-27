"""
Runs every analysis on one uploaded file in a single pass.

Called once per upload while the clean rows are still in memory. The
returned results contain only aggregated numbers and are what gets saved;
the rows themselves are discarded afterwards (privacy decision D1).
"""
from .bundling import bundle_recommendations
from .forecasting import forecast_demand
from .inventory import inventory_report
from .kpis import category_breakdown, dashboard_metrics, regional_breakdown, top_products, weekly_sales
from .pricing import DEFAULT_MARGIN, pricing_analysis, promo_inputs


def run_analysis(rows, margin=DEFAULT_MARGIN, lead_times=None):
    """Returns {result kind: JSON-ready data} for every analysis."""
    inventory = inventory_report(rows, lead_times)
    return {
        "dashboard": {
            "metrics":      dashboard_metrics(rows, inventory),
            "weekly_sales": weekly_sales(rows),
            "top_products": top_products(rows),
            "categories":   category_breakdown(rows),
            "regions":      regional_breakdown(rows),
        },
        "inventory":    inventory,
        "forecast":     forecast_demand(rows),
        "bundles":      bundle_recommendations(rows, margin),
        "pricing":      pricing_analysis(rows, margin),
        "promo_inputs": promo_inputs(rows),
    }
