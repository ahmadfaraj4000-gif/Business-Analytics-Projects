from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import *


APP_TITLE = "Spa Service Pricing Calculator"
APP_VERSION = "1.1"
THEME = "superhero"
DATA_FILE = "spa_pricing_data.json"


# -----------------------------
# Data helpers
# -----------------------------

def money(value: float) -> str:
    return f"${value:,.2f}"


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip()) if str(value).strip() else default
    except Exception:
        return default


def app_data_path() -> str:
    home = os.path.expanduser("~")
    folder = os.path.join(home, ".spa_pricing_calculator")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, DATA_FILE)


@dataclass
class Product:
    id: str
    name: str
    cost: float
    size: float
    unit: str
    notes: str = ""

    @property
    def cost_per_unit(self) -> float:
        if self.size <= 0:
            return 0.0
        return self.cost / self.size


@dataclass
class ServiceProductUsage:
    product_id: str
    amount_used: float


@dataclass
class Service:
    id: str
    name: str
    duration_minutes: float
    extra_supply_cost: float
    notes: str
    product_usages: List[ServiceProductUsage]


@dataclass
class ExtraCost:
    id: str
    name: str
    monthly_amount: float


@dataclass
class EquipmentItem:
    id: str
    name: str
    total_cost: float
    months_to_pay_off: int
    months_paid: int
    notes: str = ""

    @property
    def monthly_payment(self) -> float:
        if self.months_to_pay_off <= 0:
            return 0.0
        return self.total_cost / self.months_to_pay_off

    @property
    def is_paid_off(self) -> bool:
        return self.months_paid >= self.months_to_pay_off

    @property
    def status(self) -> str:
        return "Paid Off" if self.is_paid_off else f"{self.months_paid}/{self.months_to_pay_off} mo"


DEFAULT_DATA = {
    "business": {
        "business_name": "",
        "rent": 0.0,
        "insurance": 0.0,
        "gas": 0.0,
        "other_overhead": 0.0,
        "monthly_clients": 1.0,
        "include_labor": False,
        "hourly_rate": 0.0,
        "desired_profit_margin": 30.0,
    },
    "products": [],
    "services": [],
    "extra_costs": [],
    "equipment": [],
}


class DataStore:
    def __init__(self) -> None:
        self.path = app_data_path()
        self.data = self.load()

    def load(self) -> dict:
        if not os.path.exists(self.path):
            return json.loads(json.dumps(DEFAULT_DATA))
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for key, value in DEFAULT_DATA.items():
                if key not in loaded:
                    loaded[key] = value
            return loaded
        except Exception:
            return json.loads(json.dumps(DEFAULT_DATA))

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def products(self) -> List[Product]:
        items = []
        for p in self.data.get("products", []):
            items.append(Product(**p))
        return items

    def services(self) -> List[Service]:
        items = []
        for s in self.data.get("services", []):
            usages = [ServiceProductUsage(**u) for u in s.get("product_usages", [])]
            items.append(
                Service(
                    id=s["id"],
                    name=s["name"],
                    duration_minutes=s["duration_minutes"],
                    extra_supply_cost=s["extra_supply_cost"],
                    notes=s.get("notes", ""),
                    product_usages=usages,
                )
            )
        return items

    def extra_costs(self) -> List[ExtraCost]:
        return [ExtraCost(**e) for e in self.data.get("extra_costs", [])]

    def equipment(self) -> List[EquipmentItem]:
        items = []
        for e in self.data.get("equipment", []):
            items.append(EquipmentItem(
                id=e["id"],
                name=e["name"],
                total_cost=float(e["total_cost"]),
                months_to_pay_off=int(e["months_to_pay_off"]),
                months_paid=int(e["months_paid"]),
                notes=e.get("notes", ""),
            ))
        return items

    def product_map(self) -> Dict[str, Product]:
        return {p.id: p for p in self.products()}


# -----------------------------
# Calculation engine
# -----------------------------

class PricingEngine:
    def __init__(self, store: DataStore) -> None:
        self.store = store

    def extra_costs_total(self) -> float:
        return sum(e.monthly_amount for e in self.store.extra_costs())

    def active_equipment_monthly_total(self) -> float:
        return sum(
            item.monthly_payment
            for item in self.store.equipment()
            if not item.is_paid_off
        )

    def monthly_overhead(self) -> float:
        b = self.store.data["business"]
        return (
            float(b.get("rent", 0.0))
            + float(b.get("insurance", 0.0))
            + float(b.get("gas", 0.0))
            + float(b.get("other_overhead", 0.0))
            + self.extra_costs_total()
            + self.active_equipment_monthly_total()
        )

    def overhead_per_client(self) -> float:
        b = self.store.data["business"]
        monthly_clients = max(float(b.get("monthly_clients", 1.0)), 1.0)
        return self.monthly_overhead() / monthly_clients

    def labor_enabled(self) -> bool:
        return bool(self.store.data["business"].get("include_labor", False))

    def hourly_rate(self) -> float:
        return float(self.store.data["business"].get("hourly_rate", 0.0))

    def desired_margin_pct(self) -> float:
        return float(self.store.data["business"].get("desired_profit_margin", 30.0))

    def product_cost_for_service(self, service: Service) -> float:
        products = self.store.product_map()
        total = 0.0
        for usage in service.product_usages:
            product = products.get(usage.product_id)
            if not product:
                continue
            total += product.cost_per_unit * usage.amount_used
        return total

    def labor_cost_for_service(self, service: Service) -> float:
        if not self.labor_enabled():
            return 0.0
        hours = service.duration_minutes / 60.0
        return hours * self.hourly_rate()

    def break_even_cost(self, service: Service) -> float:
        return (
            self.overhead_per_client()
            + self.product_cost_for_service(service)
            + float(service.extra_supply_cost)
        )

    def true_cost(self, service: Service) -> float:
        return self.break_even_cost(service) + self.labor_cost_for_service(service)

    def suggested_price(self, service: Service) -> float:
        cost = self.true_cost(service) if self.labor_enabled() else self.break_even_cost(service)
        margin = self.desired_margin_pct() / 100.0
        if margin >= 1.0:
            return cost
        return cost / max(1.0 - margin, 0.01)


# -----------------------------
# UI dialogs
# -----------------------------

class ProductDialog(tb.Toplevel):
    def __init__(self, master, product: Optional[Product] = None):
        super().__init__(master)
        self.title("Product")
        self.resizable(False, False)
        self.result = None
        self.product = product
        self.transient(master)
        self.grab_set()

        frame = tb.Frame(self, padding=16)
        frame.pack(fill=BOTH, expand=YES)

        self.var_name = tk.StringVar(value=product.name if product else "")
        self.var_cost = tk.StringVar(value=str(product.cost) if product else "")
        self.var_size = tk.StringVar(value=str(product.size) if product else "")
        self.var_unit = tk.StringVar(value=product.unit if product else "ml")
        self.var_notes = tk.StringVar(value=product.notes if product else "")

        fields = [
            ("Name", self.var_name),
            ("Purchase Cost ($)", self.var_cost),
            ("Container Size", self.var_size),
            ("Unit (ml, oz, g, pumps)", self.var_unit),
            ("Notes", self.var_notes),
        ]

        for i, (label, var) in enumerate(fields):
            tb.Label(frame, text=label).grid(row=i, column=0, sticky=W, pady=6, padx=(0, 10))
            tb.Entry(frame, textvariable=var, width=34).grid(row=i, column=1, sticky=EW, pady=6)

        btns = tb.Frame(frame)
        btns.grid(row=len(fields), column=0, columnspan=2, sticky=E, pady=(12, 0))
        tb.Button(btns, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Save", bootstyle=SUCCESS, command=self.on_save).pack(side=LEFT)

        self.wait_window(self)

    def on_save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter a product name.")
            return

        cost = safe_float(self.var_cost.get())
        size = safe_float(self.var_size.get())
        unit = self.var_unit.get().strip() or "ml"
        notes = self.var_notes.get().strip()

        if size <= 0:
            messagebox.showerror("Invalid size", "Container size must be greater than 0.")
            return

        self.result = Product(
            id=self.product.id if self.product else str(uuid.uuid4()),
            name=name,
            cost=cost,
            size=size,
            unit=unit,
            notes=notes,
        )
        self.destroy()


class ServiceDialog(tb.Toplevel):
    def __init__(self, master, store: DataStore, service: Optional[Service] = None):
        super().__init__(master)
        self.title("Service")
        self.geometry("780x560")
        self.result = None
        self.store = store
        self.service = service
        self.products = store.products()
        self.product_map = {p.id: p for p in self.products}
        self.transient(master)
        self.grab_set()

        outer = tb.Frame(self, padding=16)
        outer.pack(fill=BOTH, expand=YES)

        top = tb.Labelframe(outer, text="Service Details", padding=12)
        top.pack(fill=X, pady=(0, 12))

        self.var_name = tk.StringVar(value=service.name if service else "")
        self.var_duration = tk.StringVar(value=str(service.duration_minutes) if service else "")
        self.var_supply = tk.StringVar(value=str(service.extra_supply_cost) if service else "0")
        self.var_notes = tk.StringVar(value=service.notes if service else "")

        tb.Label(top, text="Service Name").grid(row=0, column=0, sticky=W, padx=(0, 10), pady=6)
        tb.Entry(top, textvariable=self.var_name, width=32).grid(row=0, column=1, sticky=EW, pady=6)
        tb.Label(top, text="Duration (minutes)").grid(row=1, column=0, sticky=W, padx=(0, 10), pady=6)
        tb.Entry(top, textvariable=self.var_duration, width=32).grid(row=1, column=1, sticky=EW, pady=6)
        tb.Label(top, text="Extra Supplies Cost ($)").grid(row=2, column=0, sticky=W, padx=(0, 10), pady=6)
        tb.Entry(top, textvariable=self.var_supply, width=32).grid(row=2, column=1, sticky=EW, pady=6)
        tb.Label(top, text="Notes").grid(row=3, column=0, sticky=W, padx=(0, 10), pady=6)
        tb.Entry(top, textvariable=self.var_notes, width=32).grid(row=3, column=1, sticky=EW, pady=6)
        top.columnconfigure(1, weight=1)

        middle = tb.Labelframe(outer, text="Products Used In This Service", padding=12)
        middle.pack(fill=BOTH, expand=YES)

        self.tree = ttk.Treeview(middle, columns=("name", "unit", "cpu", "amount", "cost"), show="headings", height=10)
        self.tree.heading("name", text="Product")
        self.tree.heading("unit", text="Unit")
        self.tree.heading("cpu", text="Cost / Unit")
        self.tree.heading("amount", text="Amount Used")
        self.tree.heading("cost", text="Usage Cost")
        self.tree.column("name", width=220)
        self.tree.column("unit", width=100)
        self.tree.column("cpu", width=110, anchor=E)
        self.tree.column("amount", width=110, anchor=E)
        self.tree.column("cost", width=110, anchor=E)
        self.tree.pack(fill=BOTH, expand=YES)

        controls = tb.Frame(middle)
        controls.pack(fill=X, pady=(10, 0))
        self.var_product_choice = tk.StringVar()
        self.var_amount_used = tk.StringVar()

        product_names = [p.name for p in self.products] if self.products else []
        self.combo = tb.Combobox(controls, textvariable=self.var_product_choice, values=product_names, state="readonly", width=28)
        self.combo.pack(side=LEFT, padx=(0, 8))
        tb.Entry(controls, textvariable=self.var_amount_used, width=12).pack(side=LEFT, padx=(0, 8))
        tb.Button(controls, text="Add Product", bootstyle=INFO, command=self.add_usage).pack(side=LEFT, padx=(0, 8))
        tb.Button(controls, text="Remove Selected", bootstyle=DANGER, command=self.remove_usage).pack(side=LEFT)

        help_row = tb.Label(controls, text="Enter the amount used in the product's unit (ml, oz, g, etc.)", bootstyle=SECONDARY)
        help_row.pack(side=RIGHT)

        self._usage_rows: List[ServiceProductUsage] = list(service.product_usages) if service else []
        self.refresh_usage_tree()

        bottom = tb.Frame(outer)
        bottom.pack(fill=X, pady=(12, 0))
        tb.Button(bottom, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=RIGHT, padx=6)
        tb.Button(bottom, text="Save Service", bootstyle=SUCCESS, command=self.on_save).pack(side=RIGHT)

        self.wait_window(self)

    def add_usage(self):
        name = self.var_product_choice.get().strip()
        amount = safe_float(self.var_amount_used.get())
        if not name:
            messagebox.showerror("No product selected", "Please choose a product.")
            return
        if amount <= 0:
            messagebox.showerror("Invalid amount", "Amount used must be greater than 0.")
            return

        product = next((p for p in self.products if p.name == name), None)
        if not product:
            return

        self._usage_rows.append(ServiceProductUsage(product_id=product.id, amount_used=amount))
        self.var_amount_used.set("")
        self.refresh_usage_tree()

    def remove_usage(self):
        selection = self.tree.selection()
        if not selection:
            return
        idx = self.tree.index(selection[0])
        del self._usage_rows[idx]
        self.refresh_usage_tree()

    def refresh_usage_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for usage in self._usage_rows:
            product = self.product_map.get(usage.product_id)
            if not product:
                continue
            usage_cost = product.cost_per_unit * usage.amount_used
            self.tree.insert(
                "",
                END,
                values=(
                    product.name,
                    product.unit,
                    money(product.cost_per_unit),
                    f"{usage.amount_used:g}",
                    money(usage_cost),
                ),
            )

    def on_save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter a service name.")
            return
        duration = safe_float(self.var_duration.get())
        if duration <= 0:
            messagebox.showerror("Invalid duration", "Duration must be greater than 0.")
            return

        self.result = Service(
            id=self.service.id if self.service else str(uuid.uuid4()),
            name=name,
            duration_minutes=duration,
            extra_supply_cost=safe_float(self.var_supply.get()),
            notes=self.var_notes.get().strip(),
            product_usages=self._usage_rows,
        )
        self.destroy()


class ExtraCostDialog(tb.Toplevel):
    def __init__(self, master, extra_cost: Optional[ExtraCost] = None):
        super().__init__(master)
        self.title("Additional Monthly Cost")
        self.resizable(False, False)
        self.result = None
        self.extra_cost = extra_cost
        self.transient(master)
        self.grab_set()

        frame = tb.Frame(self, padding=16)
        frame.pack(fill=BOTH, expand=YES)

        self.var_name = tk.StringVar(value=extra_cost.name if extra_cost else "")
        self.var_amount = tk.StringVar(value=str(extra_cost.monthly_amount) if extra_cost else "")

        tb.Label(frame, text="Cost Name").grid(row=0, column=0, sticky=W, pady=8, padx=(0, 10))
        tb.Entry(frame, textvariable=self.var_name, width=30).grid(row=0, column=1, sticky=EW, pady=8)
        tb.Label(frame, text="Monthly Amount ($)").grid(row=1, column=0, sticky=W, pady=8, padx=(0, 10))
        tb.Entry(frame, textvariable=self.var_amount, width=30).grid(row=1, column=1, sticky=EW, pady=8)
        frame.columnconfigure(1, weight=1)

        btns = tb.Frame(frame)
        btns.grid(row=2, column=0, columnspan=2, sticky=E, pady=(12, 0))
        tb.Button(btns, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Save", bootstyle=SUCCESS, command=self.on_save).pack(side=LEFT)

        self.wait_window(self)

    def on_save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter a cost name.")
            return
        amount = safe_float(self.var_amount.get())
        self.result = ExtraCost(
            id=self.extra_cost.id if self.extra_cost else str(uuid.uuid4()),
            name=name,
            monthly_amount=amount,
        )
        self.destroy()


class EquipmentDialog(tb.Toplevel):
    def __init__(self, master, item: Optional[EquipmentItem] = None):
        super().__init__(master)
        self.title("Equipment Item")
        self.resizable(False, False)
        self.result = None
        self.item = item
        self.transient(master)
        self.grab_set()

        frame = tb.Frame(self, padding=16)
        frame.pack(fill=BOTH, expand=YES)

        self.var_name = tk.StringVar(value=item.name if item else "")
        self.var_total_cost = tk.StringVar(value=str(item.total_cost) if item else "")
        self.var_months = tk.StringVar(value=str(item.months_to_pay_off) if item else "")
        self.var_notes = tk.StringVar(value=item.notes if item else "")

        fields = [
            ("Equipment Name", self.var_name),
            ("Total Cost ($)", self.var_total_cost),
            ("Months to Pay Off", self.var_months),
            ("Notes (optional)", self.var_notes),
        ]

        for i, (label, var) in enumerate(fields):
            tb.Label(frame, text=label).grid(row=i, column=0, sticky=W, pady=8, padx=(0, 10))
            tb.Entry(frame, textvariable=var, width=30).grid(row=i, column=1, sticky=EW, pady=8)
        frame.columnconfigure(1, weight=1)

        btns = tb.Frame(frame)
        btns.grid(row=len(fields), column=0, columnspan=2, sticky=E, pady=(12, 0))
        tb.Button(btns, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Save", bootstyle=SUCCESS, command=self.on_save).pack(side=LEFT)

        self.wait_window(self)

    def on_save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Please enter an equipment name.")
            return
        total_cost = safe_float(self.var_total_cost.get())
        if total_cost <= 0:
            messagebox.showerror("Invalid cost", "Total cost must be greater than 0.")
            return
        try:
            months = int(self.var_months.get().strip())
            if months <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            messagebox.showerror("Invalid months", "Months to pay off must be a whole number greater than 0.")
            return

        months_paid = self.item.months_paid if self.item else 0

        self.result = EquipmentItem(
            id=self.item.id if self.item else str(uuid.uuid4()),
            name=name,
            total_cost=total_cost,
            months_to_pay_off=months,
            months_paid=months_paid,
            notes=self.var_notes.get().strip(),
        )
        self.destroy()


# -----------------------------
# Main application
# -----------------------------

class SpaPricingApp(tb.Window):
    def __init__(self):
        super().__init__(themename=THEME)
        self.title(f"{APP_TITLE}  •  v{APP_VERSION}")
        self.geometry("1240x820")
        self.minsize(1100, 700)

        self.store = DataStore()
        self.engine = PricingEngine(self.store)

        self.business_vars: Dict[str, tk.Variable] = {}

        self.build_ui()
        self.load_business_fields()
        self.refresh_products()
        self.refresh_services()
        self.refresh_extra_costs()
        self.refresh_equipment()
        self.refresh_dashboard()

    def build_ui(self):
        container = tb.Frame(self, padding=14)
        container.pack(fill=BOTH, expand=YES)

        title_row = tb.Frame(container)
        title_row.pack(fill=X, pady=(0, 12))

        tb.Label(title_row, text=APP_TITLE, font=("Segoe UI", 20, "bold")).pack(side=LEFT)
        tb.Label(title_row, text="A simple pricing tool for solo spa owners.", bootstyle=SECONDARY).pack(side=LEFT, padx=14, pady=(8, 0))
        tb.Button(title_row, text="Save All", bootstyle=SUCCESS, command=self.save_all).pack(side=RIGHT)

        self.notebook = tb.Notebook(container, bootstyle=PRIMARY)
        self.notebook.pack(fill=BOTH, expand=YES)

        self.tab_dashboard = tb.Frame(self.notebook, padding=16)
        self.tab_business = tb.Frame(self.notebook, padding=16)
        self.tab_products = tb.Frame(self.notebook, padding=16)
        self.tab_services = tb.Frame(self.notebook, padding=16)

        self.notebook.add(self.tab_dashboard, text="Dashboard")
        self.notebook.add(self.tab_business, text="Business Costs")
        self.notebook.add(self.tab_products, text="Products")
        self.notebook.add(self.tab_services, text="Services")

        self.build_dashboard_tab()
        self.build_business_tab()
        self.build_products_tab()
        self.build_services_tab()

    def build_dashboard_tab(self):
        top = tb.Frame(self.tab_dashboard)
        top.pack(fill=X)

        self.stat_overhead = self.make_stat_card(top, "Monthly Overhead", "-")
        self.stat_per_client = self.make_stat_card(top, "Overhead Per Client", "-")
        self.stat_products = self.make_stat_card(top, "Saved Products", "-")
        self.stat_services = self.make_stat_card(top, "Saved Services", "-")

        for card in top.winfo_children():
            card.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))

        mid = tb.Labelframe(self.tab_dashboard, text="Pricing Summary", padding=14)
        mid.pack(fill=X, pady=(18, 12))

        self.summary_text = tk.Text(mid, height=11, wrap="word", bg="#20374c", fg="white", relief="flat")
        self.summary_text.pack(fill=BOTH, expand=YES)

        bottom = tb.Labelframe(self.tab_dashboard, text="Service Cost Snapshot", padding=14)
        bottom.pack(fill=BOTH, expand=YES)

        self.dashboard_service_tree = ttk.Treeview(
            bottom,
            columns=("service", "break_even", "labor", "true_cost", "suggested"),
            show="headings",
            height=14,
        )
        for col, title, width in [
            ("service", "Service", 260),
            ("break_even", "Break-Even Cost", 140),
            ("labor", "Labor Cost", 120),
            ("true_cost", "True Cost", 120),
            ("suggested", "Suggested Price", 140),
        ]:
            self.dashboard_service_tree.heading(col, text=title)
            self.dashboard_service_tree.column(col, width=width, anchor=E if col != "service" else W)
        self.dashboard_service_tree.pack(fill=BOTH, expand=YES)

    def make_stat_card(self, parent, title: str, value: str):
        card = tb.Frame(parent, padding=14, bootstyle=DARK)
        tb.Label(card, text=title, bootstyle=SECONDARY).pack(anchor=W)
        lbl = tb.Label(card, text=value, font=("Segoe UI", 18, "bold"))
        lbl.pack(anchor=W, pady=(8, 0))
        return lbl.master

    def build_business_tab(self):
        # Use a scrollable canvas so the tab doesn't overflow
        canvas = tk.Canvas(self.tab_business, highlightthickness=0)
        scrollbar = tb.Scrollbar(self.tab_business, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)

        inner = tb.Frame(canvas, padding=4)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        inner.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=canvas.winfo_width()))

        # ---- Section 1: Core Monthly Inputs ----
        core_frame = tb.Labelframe(inner, text="Core Monthly Inputs", padding=16)
        core_frame.pack(fill=X, pady=(0, 10))

        fields = [
            ("business_name", "Business Name"),
            ("rent", "Monthly Rent ($)"),
            ("insurance", "Monthly Insurance ($)"),
            ("gas", "Monthly Gas / Travel ($)"),
            ("monthly_clients", "Monthly Clients"),
            ("hourly_rate", "Your Time Value ($/hr)"),
            ("desired_profit_margin", "Desired Profit Margin (%)"),
        ]

        for i, (key, label) in enumerate(fields):
            var = tk.StringVar()
            self.business_vars[key] = var
            tb.Label(core_frame, text=label).grid(row=i, column=0, sticky=W, pady=7, padx=(0, 10))
            tb.Entry(core_frame, textvariable=var, width=28).grid(row=i, column=1, sticky=EW, pady=7)

        self.business_vars["include_labor"] = tk.BooleanVar()
        tb.Checkbutton(
            core_frame,
            text="Include labor / time value in calculations",
            variable=self.business_vars["include_labor"],
            bootstyle="round-toggle",
            command=self.refresh_dashboard,
        ).grid(row=len(fields), column=0, columnspan=2, sticky=W, pady=(12, 6))

        tb.Button(core_frame, text="Save Business Settings", bootstyle=SUCCESS, command=self.save_business_fields).grid(
            row=len(fields) + 1, column=0, columnspan=2, sticky=EW, pady=(16, 0)
        )
        core_frame.columnconfigure(1, weight=1)

        # ---- Section 2: Additional Monthly Costs ----
        extra_frame = tb.Labelframe(inner, text="Additional Monthly Costs", padding=16)
        extra_frame.pack(fill=X, pady=(0, 10))

        tb.Label(
            extra_frame,
            text="Examples: laundry, utilities, internet, booking software, phone, cleaning, towels, music subscription.",
            bootstyle=SECONDARY,
            wraplength=700,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 8))

        extra_btn_row = tb.Frame(extra_frame)
        extra_btn_row.pack(fill=X, pady=(0, 6))
        tb.Button(extra_btn_row, text="Add Cost", bootstyle=SUCCESS, command=self.add_extra_cost).pack(side=LEFT)
        tb.Button(extra_btn_row, text="Edit Selected", bootstyle=INFO, command=self.edit_extra_cost).pack(side=LEFT, padx=8)
        tb.Button(extra_btn_row, text="Delete Selected", bootstyle=DANGER, command=self.delete_extra_cost).pack(side=LEFT)

        self.extra_cost_tree = ttk.Treeview(
            extra_frame,
            columns=("name", "amount"),
            show="headings",
            height=5,
        )
        self.extra_cost_tree.heading("name", text="Cost Name")
        self.extra_cost_tree.heading("amount", text="Monthly Amount")
        self.extra_cost_tree.column("name", width=340)
        self.extra_cost_tree.column("amount", width=160, anchor=E)
        self.extra_cost_tree.pack(fill=X)

        self.extra_cost_total_lbl = tb.Label(extra_frame, text="Total: $0.00", font=("Segoe UI", 10, "bold"))
        self.extra_cost_total_lbl.pack(anchor=E, pady=(4, 0))

        # ---- Section 3: Equipment Payments ----
        equip_frame = tb.Labelframe(inner, text="Equipment Payments", padding=16)
        equip_frame.pack(fill=X, pady=(0, 10))

        tb.Label(
            equip_frame,
            text="Track equipment you purchased on a payment plan. Each item counts toward monthly overhead until fully paid off.",
            bootstyle=SECONDARY,
            wraplength=700,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 8))

        equip_btn_row = tb.Frame(equip_frame)
        equip_btn_row.pack(fill=X, pady=(0, 6))
        tb.Button(equip_btn_row, text="Add Equipment", bootstyle=SUCCESS, command=self.add_equipment).pack(side=LEFT)
        tb.Button(equip_btn_row, text="Edit Selected", bootstyle=INFO, command=self.edit_equipment).pack(side=LEFT, padx=8)
        tb.Button(equip_btn_row, text="Delete Selected", bootstyle=DANGER, command=self.delete_equipment).pack(side=LEFT, padx=(0, 8))
        tb.Button(equip_btn_row, text="Mark One Month Paid", bootstyle=WARNING, command=self.mark_equipment_month_paid).pack(side=LEFT)

        self.equipment_tree = ttk.Treeview(
            equip_frame,
            columns=("name", "total_cost", "monthly_payment", "months_paid", "status"),
            show="headings",
            height=5,
        )
        self.equipment_tree.heading("name", text="Equipment Name")
        self.equipment_tree.heading("total_cost", text="Total Cost")
        self.equipment_tree.heading("monthly_payment", text="Monthly Payment")
        self.equipment_tree.heading("months_paid", text="Months Paid")
        self.equipment_tree.heading("status", text="Status")
        self.equipment_tree.column("name", width=220)
        self.equipment_tree.column("total_cost", width=120, anchor=E)
        self.equipment_tree.column("monthly_payment", width=140, anchor=E)
        self.equipment_tree.column("months_paid", width=110, anchor=E)
        self.equipment_tree.column("status", width=110, anchor=W)
        self.equipment_tree.pack(fill=X)

        self.equip_total_lbl = tb.Label(equip_frame, text="Active monthly total: $0.00", font=("Segoe UI", 10, "bold"))
        self.equip_total_lbl.pack(anchor=E, pady=(4, 0))

        # ---- Section 4: Business Summary ----
        summary_frame = tb.Labelframe(inner, text="Business Summary", padding=16)
        summary_frame.pack(fill=X, pady=(0, 10))

        explainer = (
            "1. Monthly Overhead = rent + insurance + gas + extra costs + active equipment payments\n\n"
            "2. Overhead Per Client = monthly overhead / monthly clients\n\n"
            "3. Break-Even Cost = overhead per client + product usage cost + extra supplies\n\n"
            "4. True Cost = break-even cost + labor cost (if enabled)\n\n"
            "5. Suggested Price = cost / (1 - desired margin)"
        )
        tb.Label(summary_frame, text=explainer, justify=LEFT, wraplength=620).pack(anchor=W)

        self.business_summary_lbl = tb.Label(summary_frame, text="", justify=LEFT, font=("Segoe UI", 11, "bold"))
        self.business_summary_lbl.pack(anchor=W, pady=(14, 0))

    def build_products_tab(self):
        top = tb.Frame(self.tab_products)
        top.pack(fill=X, pady=(0, 10))
        tb.Button(top, text="Add Product", bootstyle=SUCCESS, command=self.add_product).pack(side=LEFT)
        tb.Button(top, text="Edit Selected", bootstyle=INFO, command=self.edit_product).pack(side=LEFT, padx=8)
        tb.Button(top, text="Delete Selected", bootstyle=DANGER, command=self.delete_product).pack(side=LEFT)

        self.product_tree = ttk.Treeview(
            self.tab_products,
            columns=("name", "cost", "size", "unit", "cpu", "notes"),
            show="headings",
            height=18,
        )
        cols = [
            ("name", "Product", 220),
            ("cost", "Purchase Cost", 120),
            ("size", "Container Size", 120),
            ("unit", "Unit", 90),
            ("cpu", "Cost / Unit", 120),
            ("notes", "Notes", 280),
        ]
        for col, title, width in cols:
            self.product_tree.heading(col, text=title)
            self.product_tree.column(col, width=width, anchor=E if col in {"cost", "size", "cpu"} else W)
        self.product_tree.pack(fill=BOTH, expand=YES)

    def build_services_tab(self):
        top = tb.Frame(self.tab_services)
        top.pack(fill=X, pady=(0, 10))
        tb.Button(top, text="Add Service", bootstyle=SUCCESS, command=self.add_service).pack(side=LEFT)
        tb.Button(top, text="Edit Selected", bootstyle=INFO, command=self.edit_service).pack(side=LEFT, padx=8)
        tb.Button(top, text="Delete Selected", bootstyle=DANGER, command=self.delete_service).pack(side=LEFT)
        tb.Button(top, text="Recalculate", bootstyle=PRIMARY, command=self.refresh_services).pack(side=LEFT, padx=8)

        self.service_tree = ttk.Treeview(
            self.tab_services,
            columns=("name", "duration", "products", "break_even", "labor", "true_cost", "suggested"),
            show="headings",
            height=18,
        )
        cols = [
            ("name", "Service", 220),
            ("duration", "Minutes", 90),
            ("products", "Product Cost", 120),
            ("break_even", "Break-Even", 120),
            ("labor", "Labor", 120),
            ("true_cost", "True Cost", 120),
            ("suggested", "Suggested Price", 140),
        ]
        for col, title, width in cols:
            self.service_tree.heading(col, text=title)
            self.service_tree.column(col, width=width, anchor=E if col != "name" else W)
        self.service_tree.pack(fill=BOTH, expand=YES)

    # ---- Business fields ----

    def load_business_fields(self):
        business = self.store.data["business"]
        for key, var in self.business_vars.items():
            if key == "include_labor":
                var.set(bool(business.get(key, False)))
            else:
                var.set(str(business.get(key, "")))
        self.refresh_business_summary()

    def save_business_fields(self):
        b = self.store.data["business"]
        b["business_name"] = self.business_vars["business_name"].get().strip()
        b["rent"] = safe_float(self.business_vars["rent"].get())
        b["insurance"] = safe_float(self.business_vars["insurance"].get())
        b["gas"] = safe_float(self.business_vars["gas"].get())
        b["monthly_clients"] = max(safe_float(self.business_vars["monthly_clients"].get(), 1.0), 1.0)
        b["include_labor"] = bool(self.business_vars["include_labor"].get())
        b["hourly_rate"] = safe_float(self.business_vars["hourly_rate"].get())
        b["desired_profit_margin"] = max(safe_float(self.business_vars["desired_profit_margin"].get(), 30.0), 0.0)
        self.store.save()
        self.refresh_business_summary()
        self.refresh_dashboard()
        self.refresh_services()
        messagebox.showinfo("Saved", "Business settings saved.")

    def refresh_business_summary(self):
        total_overhead = self.engine.monthly_overhead()
        per_client = self.engine.overhead_per_client()
        extras_total = self.engine.extra_costs_total()
        equip_total = self.engine.active_equipment_monthly_total()
        include_labor = "Yes" if self.engine.labor_enabled() else "No"
        self.business_summary_lbl.configure(
            text=(
                f"Extra Monthly Costs Total:       {money(extras_total)}\n"
                f"Active Equipment Payments:       {money(equip_total)}\n"
                f"Monthly Overhead:                {money(total_overhead)}\n"
                f"Overhead Per Client:             {money(per_client)}\n"
                f"Include Labor:                   {include_labor}\n"
                f"Target Margin:                   {self.engine.desired_margin_pct():.0f}%"
            )
        )

    # ---- Extra costs ----

    def add_extra_cost(self):
        dialog = ExtraCostDialog(self)
        if not dialog.result:
            return
        self.store.data["extra_costs"].append(asdict(dialog.result))
        self.store.save()
        self.refresh_extra_costs()
        self.refresh_dashboard()
        self.refresh_services()

    def edit_extra_cost(self):
        item = self._get_selected_extra_cost()
        if not item:
            return
        dialog = ExtraCostDialog(self, item)
        if not dialog.result:
            return
        for i, e in enumerate(self.store.data["extra_costs"]):
            if e["id"] == item.id:
                self.store.data["extra_costs"][i] = asdict(dialog.result)
                break
        self.store.save()
        self.refresh_extra_costs()
        self.refresh_dashboard()
        self.refresh_services()

    def delete_extra_cost(self):
        item = self._get_selected_extra_cost()
        if not item:
            return
        if not messagebox.askyesno("Delete cost", f"Delete '{item.name}'?"):
            return
        self.store.data["extra_costs"] = [e for e in self.store.data["extra_costs"] if e["id"] != item.id]
        self.store.save()
        self.refresh_extra_costs()
        self.refresh_dashboard()
        self.refresh_services()

    def _get_selected_extra_cost(self) -> Optional[ExtraCost]:
        selection = self.extra_cost_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a cost item.")
            return None
        selected_id = selection[0]
        return next((e for e in self.store.extra_costs() if e.id == selected_id), None)

    def refresh_extra_costs(self):
        for row in self.extra_cost_tree.get_children():
            self.extra_cost_tree.delete(row)
        total = 0.0
        for ec in self.store.extra_costs():
            self.extra_cost_tree.insert("", END, iid=ec.id, values=(ec.name, money(ec.monthly_amount)))
            total += ec.monthly_amount
        self.extra_cost_total_lbl.configure(text=f"Total: {money(total)}")
        self.refresh_business_summary()

    # ---- Equipment ----

    def add_equipment(self):
        dialog = EquipmentDialog(self)
        if not dialog.result:
            return
        self.store.data["equipment"].append(asdict(dialog.result))
        self.store.save()
        self.refresh_equipment()
        self.refresh_dashboard()
        self.refresh_services()

    def edit_equipment(self):
        item = self._get_selected_equipment()
        if not item:
            return
        dialog = EquipmentDialog(self, item)
        if not dialog.result:
            return
        for i, e in enumerate(self.store.data["equipment"]):
            if e["id"] == item.id:
                self.store.data["equipment"][i] = asdict(dialog.result)
                break
        self.store.save()
        self.refresh_equipment()
        self.refresh_dashboard()
        self.refresh_services()

    def delete_equipment(self):
        item = self._get_selected_equipment()
        if not item:
            return
        if not messagebox.askyesno("Delete equipment", f"Delete '{item.name}'?"):
            return
        self.store.data["equipment"] = [e for e in self.store.data["equipment"] if e["id"] != item.id]
        self.store.save()
        self.refresh_equipment()
        self.refresh_dashboard()
        self.refresh_services()

    def mark_equipment_month_paid(self):
        item = self._get_selected_equipment()
        if not item:
            return
        if item.is_paid_off:
            messagebox.showinfo("Already paid off", f"'{item.name}' is already fully paid off.")
            return

        for e in self.store.data["equipment"]:
            if e["id"] == item.id:
                e["months_paid"] = e["months_paid"] + 1
                newly_paid_off = e["months_paid"] >= e["months_to_pay_off"]
                break

        self.store.save()
        self.refresh_equipment()
        self.refresh_dashboard()
        self.refresh_services()

        if newly_paid_off:
            messagebox.showinfo(
                "Equipment Paid Off!",
                f"Congratulations! '{item.name}' is now fully paid off.\n\n"
                "It will no longer count toward your monthly overhead."
            )

    def _get_selected_equipment(self) -> Optional[EquipmentItem]:
        selection = self.equipment_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select an equipment item.")
            return None
        selected_id = selection[0]
        return next((e for e in self.store.equipment() if e.id == selected_id), None)

    def refresh_equipment(self):
        for row in self.equipment_tree.get_children():
            self.equipment_tree.delete(row)
        active_total = 0.0
        for item in self.store.equipment():
            if not item.is_paid_off:
                active_total += item.monthly_payment
            self.equipment_tree.insert(
                "", END, iid=item.id,
                values=(
                    item.name,
                    money(item.total_cost),
                    money(item.monthly_payment),
                    f"{item.months_paid} / {item.months_to_pay_off}",
                    item.status,
                ),
            )
        self.equip_total_lbl.configure(text=f"Active monthly total: {money(active_total)}")
        self.refresh_business_summary()

    # ---- Products ----

    def add_product(self):
        dialog = ProductDialog(self)
        if not dialog.result:
            return
        self.store.data["products"].append(asdict(dialog.result))
        self.store.save()
        self.refresh_products()
        self.refresh_services()
        self.refresh_dashboard()

    def edit_product(self):
        product = self.get_selected_product()
        if not product:
            return
        dialog = ProductDialog(self, product)
        if not dialog.result:
            return
        products = self.store.data["products"]
        for i, item in enumerate(products):
            if item["id"] == product.id:
                products[i] = asdict(dialog.result)
                break
        self.store.save()
        self.refresh_products()
        self.refresh_services()
        self.refresh_dashboard()

    def delete_product(self):
        product = self.get_selected_product()
        if not product:
            return
        if not messagebox.askyesno("Delete product", f"Delete '{product.name}'?"):
            return
        self.store.data["products"] = [p for p in self.store.data["products"] if p["id"] != product.id]
        for svc in self.store.data["services"]:
            svc["product_usages"] = [u for u in svc.get("product_usages", []) if u["product_id"] != product.id]
        self.store.save()
        self.refresh_products()
        self.refresh_services()
        self.refresh_dashboard()

    def refresh_products(self):
        for row in self.product_tree.get_children():
            self.product_tree.delete(row)
        for product in self.store.products():
            self.product_tree.insert(
                "",
                END,
                iid=product.id,
                values=(
                    product.name,
                    money(product.cost),
                    f"{product.size:g}",
                    product.unit,
                    money(product.cost_per_unit),
                    product.notes,
                ),
            )
        self.refresh_business_summary()

    # ---- Services ----

    def add_service(self):
        if not self.store.products():
            messagebox.showwarning("Add products first", "Please add at least one product before creating a service.")
            return
        dialog = ServiceDialog(self, self.store)
        if not dialog.result:
            return
        payload = asdict(dialog.result)
        payload["product_usages"] = [asdict(u) for u in dialog.result.product_usages]
        self.store.data["services"].append(payload)
        self.store.save()
        self.refresh_services()
        self.refresh_dashboard()

    def edit_service(self):
        service = self.get_selected_service()
        if not service:
            return
        dialog = ServiceDialog(self, self.store, service)
        if not dialog.result:
            return
        payload = asdict(dialog.result)
        payload["product_usages"] = [asdict(u) for u in dialog.result.product_usages]
        for i, item in enumerate(self.store.data["services"]):
            if item["id"] == service.id:
                self.store.data["services"][i] = payload
                break
        self.store.save()
        self.refresh_services()
        self.refresh_dashboard()

    def delete_service(self):
        service = self.get_selected_service()
        if not service:
            return
        if not messagebox.askyesno("Delete service", f"Delete '{service.name}'?"):
            return
        self.store.data["services"] = [s for s in self.store.data["services"] if s["id"] != service.id]
        self.store.save()
        self.refresh_services()
        self.refresh_dashboard()

    def refresh_services(self):
        for row in self.service_tree.get_children():
            self.service_tree.delete(row)

        services = self.store.services()
        for service in services:
            product_cost = self.engine.product_cost_for_service(service)
            break_even = self.engine.break_even_cost(service)
            labor = self.engine.labor_cost_for_service(service)
            true_cost = self.engine.true_cost(service)
            suggested = self.engine.suggested_price(service)
            self.service_tree.insert(
                "",
                END,
                iid=service.id,
                values=(
                    service.name,
                    f"{service.duration_minutes:g}",
                    money(product_cost),
                    money(break_even),
                    money(labor),
                    money(true_cost),
                    money(suggested),
                ),
            )
        self.refresh_dashboard()

    # ---- Dashboard ----

    def refresh_dashboard(self):
        self.refresh_business_summary()
        business_name = self.store.data["business"].get("business_name", "") or "Your Spa"
        services = self.store.services()
        products = self.store.products()

        dashboard_cards = self.tab_dashboard.winfo_children()[0].winfo_children()
        dashboard_cards[0].winfo_children()[1].configure(text=money(self.engine.monthly_overhead()))
        dashboard_cards[1].winfo_children()[1].configure(text=money(self.engine.overhead_per_client()))
        dashboard_cards[2].winfo_children()[1].configure(text=str(len(products)))
        dashboard_cards[3].winfo_children()[1].configure(text=str(len(services)))

        self.summary_text.configure(state=NORMAL)
        self.summary_text.delete("1.0", END)
        self.summary_text.insert(
            END,
            f"{business_name}\n\n"
            f"Extra monthly costs:  {money(self.engine.extra_costs_total())}\n"
            f"Active equipment:     {money(self.engine.active_equipment_monthly_total())}\n"
            f"Monthly overhead:     {money(self.engine.monthly_overhead())}\n"
            f"Overhead per client:  {money(self.engine.overhead_per_client())}\n"
            f"Labor included:       {'Yes' if self.engine.labor_enabled() else 'No'}\n"
            f"Your time value:      {money(self.engine.hourly_rate())}/hr\n"
            f"Desired profit margin: {self.engine.desired_margin_pct():.0f}%\n\n"
            f"Tip: Break-even cost shows the minimum to cover all expenses.\n"
            f"True cost adds your time value when labor is enabled.\n"
            f"Suggested price applies your target profit margin to the cost basis."
        )

        for row in self.dashboard_service_tree.get_children():
            self.dashboard_service_tree.delete(row)
        for service in services:
            self.dashboard_service_tree.insert(
                "",
                END,
                values=(
                    service.name,
                    money(self.engine.break_even_cost(service)),
                    money(self.engine.labor_cost_for_service(service)),
                    money(self.engine.true_cost(service)),
                    money(self.engine.suggested_price(service)),
                ),
            )

    # ---- Helpers ----

    def get_selected_product(self) -> Optional[Product]:
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a product.")
            return None
        selected_id = selection[0]
        return next((p for p in self.store.products() if p.id == selected_id), None)

    def get_selected_service(self) -> Optional[Service]:
        selection = self.service_tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a service.")
            return None
        selected_id = selection[0]
        return next((s for s in self.store.services() if s.id == selected_id), None)

    def save_all(self):
        self.save_business_fields()


if __name__ == "__main__":
    app = SpaPricingApp()
    app.mainloop()
