from dataclasses import dataclass
from typing import Optional

@dataclass
class Ingredient:
    name: str
    purchase_price: float
    purchase_qty: float
    purchase_unit: str
    recipe_qty_used: float
    recipe_unit: str
    waste_pct: float = 0.0  # decimal; 0 uses global default

@dataclass
class ScenarioInputs:
    """
    What-if adjustments:
    - global_ingredient_price_pct: apply to ALL ingredient purchase prices (e.g. 0.15 = +15%)
    - specific_ingredient_name + specific_ingredient_price_pct: apply to ONE ingredient
    - labor_delta_per_hour: +$ amount (e.g. 2 = +$2/hr)
    - overhead_pct: % change to monthly overhead (e.g. 0.10 = +10%)
    - volume_pct: % change to monthly units sold (e.g. -0.20 = -20%)
    """
    global_ingredient_price_pct: float = 0.0
    specific_ingredient_name: Optional[str] = None
    specific_ingredient_price_pct: float = 0.0
    labor_delta_per_hour: float = 0.0
    overhead_pct: float = 0.0
    volume_pct: float = 0.0

@dataclass
class ItemPricingInputs:
    item_name: str
    ingredients: list[Ingredient]

    # Costs
    labor_hourly_rate: float
    labor_minutes_per_item: float
    monthly_overhead: float
    monthly_units_sold: float

    # Pricing targets
    target_margin: float  # decimal
    current_price: Optional[float] = None
    default_waste_pct: float = 0.0

    # Competitors
    competitor_prices: Optional[list[float]] = None

    # Batch Calculator
    prep_time_hours: float = 0.0
    prep_time_minutes: float = 40.0
    batch_yield: float = 10.0
    labor_minutes_auto: bool = True

    # Toggles
    auto_min_viable: bool = True
    min_viable_margin: float = 0.10  # used if auto_min_viable
    premium_positioning: bool = False
    premium_cap_over_comp_max_pct: float = 0.10  # if premium_positioning, allow +10% over comp max

    # Transaction fees (% of sale price — applied to break-even AND profitable price)
    cc_fee_pct: float = 0.0   # e.g. 0.026 = 2.6%
    app_fee_pct: float = 0.0  # e.g. 0.15 = 15%

@dataclass
class PricingResults:
    food_cost: float
    waste_cost: float
    labor_cost: float
    overhead_cost: float
    true_cost: float          # all hard costs (food+waste+labor+overhead+pkg)

    break_even_price: float   # minimum price covering true_cost + transaction fees
    recommended_price: float  # break_even_price / (1 - target_margin)

    cc_fee_pct: float         # blended CC fee used in calculation
    app_fee_pct: float        # blended app fee used in calculation

    profit_per_item_at_current: Optional[float]
    margin_pct_at_current: Optional[float]
    status_label: Optional[str]

    competitor_min: Optional[float]
    competitor_max: Optional[float]
    competitor_avg: Optional[float]
    competitor_rows: list[dict]  # [{price, profit, margin_pct}]

    competitive_profitable_price: Optional[float]
    max_margin_if_match_comp_avg: Optional[float]
