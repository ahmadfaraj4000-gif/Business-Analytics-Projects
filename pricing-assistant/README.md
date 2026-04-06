# Pricing Assistant – Python Pricing Engine

Pricing Assistant is a desktop application built in Python that translates economic cost theory into practical pricing decisions for restaurants and service-based businesses.

It enables users to model real-world cost structures—including ingredients, labor, overhead, and waste—and generate breakeven and profit-optimized pricing recommendations.

---

## Overview

This tool was designed to solve a common problem in small businesses: pricing is often based on guesswork rather than structured cost analysis.

Pricing Assistant applies core economic principles such as:

* Cost of Goods Sold (COGS)
* Marginal cost awareness
* Overhead allocation
* Profit margin targeting

to provide clear, data-driven pricing outputs.

---

## Key Features

### Ingredient-Level Cost Modeling

* Define purchase cost, quantity, and units (lb, oz, g, ml, etc.)
* Automatically calculates cost per unit
* Converts ingredient usage into per-item cost

### Waste Adjustment

* Apply waste percentages to reflect real-world inefficiencies
* Supports both per-ingredient and global waste assumptions

### Labor Cost Integration

* Supports fixed labor or weighted labor tiers
* Calculates labor cost per item based on time and wage inputs

### Overhead Allocation

* Input detailed monthly overhead categories (rent, utilities, etc.)
* Distributes overhead across production volume
* Provides per-item overhead cost contribution

### Pricing Engine

* Calculates:

  * Breakeven cost
  * True cost (including labor)
  * Suggested price based on target margin
* Ensures margin constraints are respected

### Scenario Analysis (Pro Logic)

* Supports “what-if” adjustments to:

  * Costs
  * labor
  * margins
* Helps evaluate pricing sensitivity and decision impact

### Data Persistence

* Saves and loads pricing profiles
* Uses structured JSON storage for reproducibility and analysis over time

---

## Example Pricing Logic

The application uses a structured pricing model:

Suggested Price = Total Cost ÷ (1 - Target Margin)

Where Total Cost includes:

* Ingredient cost
* Waste-adjusted inputs
* Labor cost
* Allocated overhead

---

## Tech Stack

* Python
* Tkinter / ttkbootstrap (desktop UI)
* JSON (data storage and persistence)

---

## How to Run

1. Install dependencies:

```bash
pip install ttkbootstrap
```

2. Run the application:

```bash
python main.py
```

---

## Project Structure

```plaintext
pricing-engine/
├── main.py
├── calculator.py
├── models.py
├── storage.py
├── README.md
```

---

## Use Cases

* Restaurant menu pricing
* Food cost analysis
* Service-based pricing (e.g., salons, spas)
* Small business cost modeling
* Margin optimization and pricing strategy

---

## Key Takeaway

This project demonstrates how economic theory can be operationalized into real software tools that improve business decision-making.

Rather than relying on intuition, users can price products and services based on structured cost inputs and measurable financial targets.

---

## Author

Ahmad Faraj
Business Analytics & Applied Economics
GitHub: https://github.com/ahmadfaraj4000-gif/Business-Analytics-Projects
