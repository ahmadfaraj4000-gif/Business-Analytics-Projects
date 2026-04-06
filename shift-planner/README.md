# Shift Planner – Workforce Scheduling & Labor Cost Analysis Tool

Shift Planner is a Python-based desktop application designed to help service businesses build weekly employee schedules while analyzing labor costs and labor efficiency in real time.

The tool combines workforce scheduling with financial insight by linking employee shifts directly to labor cost and revenue projections, enabling better staffing decisions before schedules are finalized.

---

## Overview

Labor is one of the largest and most controllable costs in service-based businesses. However, scheduling is often done without clear visibility into how staffing decisions impact profitability.

Shift Planner applies operational and financial modeling principles to answer key questions:

* How much will this schedule cost in labor?
* Is my staffing level aligned with projected revenue?
* What is my labor cost as a percentage of sales?

By integrating scheduling and cost analysis into a single interface, the application enables more efficient workforce planning and cost control.

---

## Key Features

### Weekly Schedule Builder

* Create and manage a full 7-day schedule (Monday–Sunday)
* Assign employees to shifts with start and end times
* Supports overnight shifts and flexible scheduling

### Employee Management

* Store employee details including:

  * Name
  * Role
  * Hourly wage
  * Maximum weekly hours
  * Availability constraints (unavailable days)
* Color-coded employees for visual clarity in the schedule

### Real-Time Labor Cost Calculation

* Automatically calculates labor cost per shift:

  * Wage × hours worked
* Aggregates:

  * Daily labor cost
  * Weekly labor cost

### Labor % of Revenue Analysis

* Input projected revenue (daily or weekly)
* Calculates labor as a percentage of revenue
* Helps identify overstaffing or understaffing before the week begins

### Revenue Modes

* Supports:

  * Daily revenue inputs
  * Weekly revenue projections
* Enables flexible forecasting depending on business needs

### Data Persistence

* Saves schedules as structured JSON files
* Stores:

  * employees
  * shifts
  * revenue inputs
  * schedule metadata
* Allows users to:

  * load past schedules
  * reuse templates
  * export schedules

### Schedule Management

* Save, load, rename, and delete schedules
* Export schedules to CSV for external use
* Maintain a persistent employee database

---

## Core Calculations

### Shift Hours

Calculated from start and end time (supports overnight shifts):

Shift Hours = End Time - Start Time

### Shift Cost

Shift Cost = Hourly Wage × Shift Hours

### Labor Percentage

Labor % = Total Labor Cost ÷ Revenue

---

## Tech Stack

* Python
* Tkinter / ttkbootstrap (desktop UI)
* JSON (data storage and persistence)
* CSV export functionality

---

## How to Run

1. Install dependencies:

```bash
pip install ttkbootstrap
```

2. Run the application:

```bash
python shift_planner.py
```

---

## Project Structure

```plaintext
shift-planner/
├── shift_planner.py
├── README.md
```

---

## Use Cases

* Restaurant and retail scheduling
* Labor cost planning and forecasting
* Workforce optimization
* Revenue-to-labor ratio analysis
* Small business operations management

---

## Key Takeaway

This project demonstrates how operational workflows (employee scheduling) can be integrated with financial analysis to improve decision-making.

By linking staffing decisions directly to labor cost and revenue impact, businesses can proactively manage one of their most critical expenses.

---


## Author

Ahmad Faraj
Business Analytics & Applied Economics
GitHub: https://github.com/ahmadfaraj4000-gif/Business-Analytics-Projects
