# Service Cost Calculator – Cost Per Client & Profitability Engine

Service Cost Calculator is a Python-based desktop application designed for service businesses (such as spas, salons, and independent operators) to accurately determine cost per client, true service cost, and profitable pricing.

The application models real-world operating conditions by incorporating overhead, product usage, labor, and equipment amortization into a unified cost framework.

---

## Overview

Many service-based businesses underestimate their true costs by ignoring overhead allocation and long-term expenses such as equipment.

This tool applies financial and economic modeling principles to answer critical questions:

* What does each client actually cost me?
* Am I pricing my services profitably?
* How do overhead and equipment impact my margins?

By translating these concepts into a usable interface, the application enables more informed pricing and operational decisions.

---

## Key Features

### Cost Per Client Calculation

* Aggregates all monthly business expenses
* Divides total costs across expected monthly client volume
* Produces an accurate per-client cost baseline

### Overhead Modeling

* Tracks fixed monthly costs including:

  * Rent
  * Insurance
  * Transportation (e.g., gas)
  * Additional business expenses
* Supports custom extra cost categories

### Equipment Amortization

* Models large purchases over time
* Distributes equipment cost across months
* Automatically excludes fully paid-off items
* Tracks payoff progress and status

### Product Usage Tracking

* Defines product cost and container size
* Calculates cost per unit
* Applies usage per service to determine true product cost

### Service-Level Cost Analysis

* Calculates:

  * Product cost per service
  * Additional supply cost
  * Overhead per client
* Produces:

  * Break-even cost
  * True cost (with labor if enabled)
  * Suggested price based on margin

### Labor Cost Integration

* Optional labor toggle
* Calculates cost based on:

  * Service duration
  * Hourly rate
* Seamlessly integrates into total cost

### Profit Margin Targeting

* User-defined desired profit margin
* Generates suggested pricing based on cost structure
* Prevents underpricing by enforcing margin logic

### Data Persistence

* Stores all data locally using JSON
* Maintains:

  * products
  * services
  * business settings
  * equipment
* Allows users to revisit and adjust past scenarios

---

## Pricing Logic

The application calculates pricing using:

Suggested Price = Total Cost ÷ (1 - Margin)

Where Total Cost includes:

* Product usage cost
* Overhead allocation per client
* Additional service supplies
* Labor cost (if enabled)

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
python spa_pricing_calculator.py
```

---

## Project Structure

```plaintext
service-cost-calculator/
├── spa_pricing_calculator.py
├── README.md
```

---

## Use Cases

* Spa and salon pricing optimization
* Service-based cost analysis
* Small business financial planning
* Equipment investment tracking
* Profit margin validation

---

## Key Takeaway

This project demonstrates how financial modeling and economic principles can be applied to service businesses to improve pricing accuracy and profitability.

By accounting for overhead, labor, and long-term costs, businesses can move from guesswork to structured, data-driven pricing decisions.

---

## Author

Ahmad Faraj
Business Analytics & Applied Economics
GitHub: https://github.com/ahmadfaraj4000-gif/Business-Analytics-Projects
