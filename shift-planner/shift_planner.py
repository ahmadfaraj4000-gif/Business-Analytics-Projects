
"""
Shift Planner — Faraj Software Solutions
Enhanced MVP
Requires: pip install ttkbootstrap
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import ttkbootstrap as tb

# ── App metadata ─────────────────────────────────────────────
APP_TITLE = "Shift Planner"
APP_VER = "1.1"
THEME = "superhero"

# ── Palette ──────────────────────────────────────────────────
C_BG = "#2b3e50"
C_CARD = "#1a2a3a"
C_CARD2 = "#243344"
C_GOLD = "#FFD700"
C_GREEN = "#4CAF50"
C_RED = "#e74c3c"
C_ORANGE = "#f39c12"
C_MUTED = "#7f9db9"
C_TEAL = "#22d3c5"
C_TEXT = "#dce8f5"
C_WARNING = "#f39c12"

EMP_COLORS = [
    {"bg": "#1a3a2a", "fg": "#2ecc71"},
    {"bg": "#1a2a3a", "fg": "#22d3c5"},
    {"bg": "#2a1a3a", "fg": "#9b59b6"},
    {"bg": "#3a2a1a", "fg": "#f39c12"},
    {"bg": "#2a1a1a", "fg": "#e74c3c"},
    {"bg": "#1a2a1a", "fg": "#27ae60"},
    {"bg": "#1a1a3a", "fg": "#3498db"},
    {"bg": "#3a1a2a", "fg": "#e91e8c"},
]

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── Helpers ──────────────────────────────────────────────────
def ffloat(s, default=0.0):
    try:
        text = str(s).strip()
        if not text or text == "Weekly revenue":
            return default
        return float(text)
    except Exception:
        return default


def fmt_money(x):
    return f"${x:,.2f}"


def shift_hours(start: str, end: str) -> float:
    sh, sm = int(start[:2]), int(start[3:])
    eh, em = int(end[:2]), int(end[3:])
    mins = (eh * 60 + em) - (sh * 60 + sm)
    if mins < 0:
        mins += 24 * 60
    return mins / 60.0


def shift_cost(wage: float, start: str, end: str) -> float:
    return wage * shift_hours(start, end)


def week_monday(offset: int = 0) -> date:
    today = date.today()
    mon = today - timedelta(days=today.weekday())
    return mon + timedelta(weeks=offset)


def safe_name(s: str) -> str:
    return "".join(c for c in s.strip() if c.isalnum() or c in " -_").strip().replace(" ", "_") or "Schedule"


# ── App data directory ───────────────────────────────────────
def app_base_dir() -> str:
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = os.path.join(appdata, "Shift Planner")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support", "Shift Planner")
    else:
        base = os.path.join(home, ".local", "share", "Shift Planner")
    os.makedirs(base, exist_ok=True)
    return base


def schedules_dir() -> str:
    path = os.path.join(app_base_dir(), "schedules")
    os.makedirs(path, exist_ok=True)
    return path


def employees_dir() -> str:
    return app_base_dir()


def list_saved_schedules() -> List[str]:
    d = schedules_dir()
    paths = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".json")]
    paths.sort()
    return paths


def make_schedule_path(name: str) -> str:
    return os.path.join(schedules_dir(), safe_name(name) + ".json")


def make_employees_path() -> str:
    return os.path.join(employees_dir(), "employees.json")


# ── Data models ──────────────────────────────────────────────
class Employee:
    _counter = 0

    def __init__(
        self,
        name,
        role,
        wage,
        emp_id=None,
        color_idx=0,
        max_hours: float = 40.0,
        unavailable_days: Optional[List[int]] = None,
    ):
        if emp_id is None:
            Employee._counter += 1
            self.emp_id = Employee._counter
        else:
            self.emp_id = emp_id
            Employee._counter = max(Employee._counter, emp_id)

        self.name = name
        self.role = role
        self.wage = wage
        self.color_idx = color_idx
        self.max_hours = max_hours
        self.unavailable_days = sorted(set(unavailable_days or []))

    def color(self):
        return EMP_COLORS[self.color_idx % len(EMP_COLORS)]

    def initials(self):
        parts = self.name.strip().split()
        return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else self.name[:2].upper()

    def is_available(self, day_idx: int) -> bool:
        return day_idx not in self.unavailable_days

    def to_dict(self):
        return {
            "emp_id": self.emp_id,
            "name": self.name,
            "role": self.role,
            "wage": self.wage,
            "color_idx": self.color_idx,
            "max_hours": self.max_hours,
            "unavailable_days": self.unavailable_days,
        }

    @staticmethod
    def from_dict(d):
        return Employee(
            d["name"],
            d.get("role", ""),
            d["wage"],
            emp_id=d["emp_id"],
            color_idx=d.get("color_idx", 0),
            max_hours=d.get("max_hours", 40.0),
            unavailable_days=d.get("unavailable_days", []),
        )


class Shift:
    def __init__(self, emp_id, day_idx, start, end):
        self.emp_id = emp_id
        self.day_idx = day_idx
        self.start = start
        self.end = end

    @property
    def key(self):
        return f"{self.emp_id}-{self.day_idx}"

    def to_dict(self):
        return {"emp_id": self.emp_id, "day_idx": self.day_idx, "start": self.start, "end": self.end}

    @staticmethod
    def from_dict(d):
        return Shift(d["emp_id"], d["day_idx"], d["start"], d["end"])


class ScheduleRecord:
    """One saved schedule (employees + shifts + metadata)."""

    def __init__(
        self,
        name: str,
        employees: List[Employee],
        shifts: Dict[str, Shift],
        revenue: str = "",
        week_label: str = "",
        created_at: str = "",
        daily_revenue: Optional[List[str]] = None,
        coverage_targets: Optional[List[str]] = None,
        revenue_mode: str = "daily",
    ):
        self.name = name
        self.employees = employees
        self.shifts = shifts
        self.revenue = revenue
        self.week_label = week_label
        self.created_at = created_at or datetime.now().isoformat()
        self.daily_revenue = list(daily_revenue or [""] * 7)
        self.coverage_targets = list(coverage_targets or [""] * 7)
        self.revenue_mode = revenue_mode

    def to_dict(self):
        return {
            "version": 4,
            "name": self.name,
            "created_at": self.created_at,
            "week_label": self.week_label,
            "revenue": self.revenue,
            "daily_revenue": self.daily_revenue,
            "coverage_targets": self.coverage_targets,
            "revenue_mode": self.revenue_mode,
            "employees": [e.to_dict() for e in self.employees],
            "shifts": [s.to_dict() for s in self.shifts.values()],
        }

    @staticmethod
    def from_dict(d):
        emps = [Employee.from_dict(x) for x in d.get("employees", [])]
        shifts = {f"{s['emp_id']}-{s['day_idx']}": Shift.from_dict(s) for s in d.get("shifts", [])}
        return ScheduleRecord(
            name=d.get("name", "Unnamed"),
            employees=emps,
            shifts=shifts,
            revenue=d.get("revenue", ""),
            week_label=d.get("week_label", ""),
            created_at=d.get("created_at", ""),
            daily_revenue=d.get("daily_revenue", [""] * 7),
            coverage_targets=d.get("coverage_targets", [""] * 7),
            revenue_mode=d.get("revenue_mode", "daily"),
        )


def save_schedule_to_disk(path: str, rec: ScheduleRecord):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec.to_dict(), f, indent=2)


def load_schedule_from_disk(path: str) -> ScheduleRecord:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return ScheduleRecord.from_dict(d)


def save_employees_to_disk(employees: List[Employee]):
    path = make_employees_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in employees], f, indent=2)


def load_employees_from_disk() -> List[Employee]:
    path = make_employees_path()
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    emps = [Employee.from_dict(d) for d in data]
    if emps:
        Employee._counter = max(e.emp_id for e in emps)
    return emps


# ── Dialogs ──────────────────────────────────────────────────
class EmployeeDialog(tk.Toplevel):
    def __init__(self, parent, initial: Optional[Employee] = None):
        super().__init__(parent)
        self.title("Edit Employee" if initial else "Add Employee")
        self.resizable(False, False)
        self.result: Optional[Employee] = None
        self._initial = initial

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        self.var_name = tk.StringVar(value=initial.name if initial else "")
        self.var_role = tk.StringVar(value=initial.role if initial else "")
        self.var_wage = tk.StringVar(value=str(initial.wage) if initial else "")
        self.var_max_hours = tk.StringVar(value=str(initial.max_hours if initial else 40))

        def row(label, widget, r, hint=""):
            ttk.Label(frm, text=label, font=("Segoe UI", 10, "bold")).grid(row=r * 2, column=0, sticky="w", pady=(8, 2))
            widget.grid(row=r * 2, column=1, sticky="ew", padx=(12, 0), pady=(8, 2))
            if hint:
                ttk.Label(frm, text=hint, font=("Segoe UI", 9, "italic"), foreground=C_MUTED).grid(
                    row=r * 2 + 1, column=0, columnspan=2, sticky="w", pady=(0, 2)
                )
            frm.grid_columnconfigure(1, weight=1)

        row("Full Name", ttk.Entry(frm, textvariable=self.var_name, width=28), 0)
        row("Role / Title", ttk.Entry(frm, textvariable=self.var_role, width=28), 1, "e.g. Manager, Cook, Server")
        row("Hourly Wage ($)", ttk.Entry(frm, textvariable=self.var_wage, width=28), 2, "Regular hourly rate")
        row("Max Weekly Hours", ttk.Entry(frm, textvariable=self.var_max_hours, width=28), 3, "Used for overtime warnings")

        ttk.Label(frm, text="Unavailable Days", font=("Segoe UI", 10, "bold")).grid(row=8, column=0, sticky="w", pady=(8, 4))
        day_box = ttk.Frame(frm)
        day_box.grid(row=8, column=1, sticky="w", padx=(12, 0), pady=(8, 4))

        self.day_vars = []
        unavailable = set(initial.unavailable_days if initial else [])
        for i, day in enumerate(DAYS):
            var = tk.BooleanVar(value=i in unavailable)
            self.day_vars.append(var)
            ttk.Checkbutton(day_box, text=day, variable=var, bootstyle="round-toggle").grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="w")

        ttk.Separator(frm).grid(row=10, column=0, columnspan=2, sticky="ew", pady=12)
        btns = ttk.Frame(frm)
        btns.grid(row=11, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Cancel", bootstyle="secondary-outline", command=self.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="  Save  ", bootstyle="primary", command=self._save).grid(row=0, column=1)

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent)
        self.grab_set()
        self.wait_visibility()
        self.focus_force()
        self.wait_window(self)

    def _save(self):
        name = self.var_name.get().strip()
        wage = ffloat(self.var_wage.get())
        max_hours = ffloat(self.var_max_hours.get(), 40.0)
        if not name:
            messagebox.showerror("Missing", "Name is required.", parent=self)
            return
        if wage <= 0:
            messagebox.showerror("Invalid", "Hourly wage must be > 0.", parent=self)
            return
        if max_hours <= 0:
            messagebox.showerror("Invalid", "Max weekly hours must be > 0.", parent=self)
            return
        ci = self._initial.color_idx if self._initial else 0
        eid = self._initial.emp_id if self._initial else None
        unavailable_days = [i for i, var in enumerate(self.day_vars) if var.get()]
        self.result = Employee(
            name,
            self.var_role.get().strip(),
            wage,
            emp_id=eid,
            color_idx=ci,
            max_hours=max_hours,
            unavailable_days=unavailable_days,
        )
        self.destroy()


class ShiftDialog(tk.Toplevel):
    def __init__(self, parent, emp: Employee, day_name: str, initial: Optional[Shift] = None):
        super().__init__(parent)
        self.title(f"{'Edit' if initial else 'Add'} Shift — {emp.name}")
        self.resizable(False, False)
        self.result = None
        self._emp = emp

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        c = emp.color()
        hdr = ttk.Frame(frm)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(hdr, text=emp.initials(), font=("Segoe UI", 14, "bold"), foreground=c["fg"], background=c["bg"], width=3, anchor="center").pack(side="left", padx=(0, 10))
        info = ttk.Frame(hdr)
        info.pack(side="left")
        ttk.Label(info, text=emp.name, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(info, text=f"{day_name}  ·  ${emp.wage:.2f}/hr  ·  Max {emp.max_hours:.1f}h", font=("Segoe UI", 9), foreground=C_MUTED).pack(anchor="w")

        self.var_start = tk.StringVar(value=initial.start if initial else "09:00")
        self.var_end = tk.StringVar(value=initial.end if initial else "17:00")

        def row(label, widget, r):
            ttk.Label(frm, text=label, font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=6)
            widget.grid(row=r, column=1, sticky="ew", padx=(12, 0), pady=6)
            frm.grid_columnconfigure(1, weight=1)

        row("Start Time", ttk.Entry(frm, textvariable=self.var_start, width=10), 1)
        row("End Time", ttk.Entry(frm, textvariable=self.var_end, width=10), 2)
        ttk.Label(frm, text="Format: HH:MM (24-hr)  e.g. 09:00, 17:30", font=("Segoe UI", 9), foreground=C_MUTED).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.var_preview = tk.StringVar()
        ttk.Label(frm, textvariable=self.var_preview, font=("Segoe UI", 12, "bold"), foreground=C_TEAL).grid(row=4, column=0, columnspan=2, pady=8)

        self._update_preview()
        self.var_start.trace_add("write", lambda *_: self._update_preview())
        self.var_end.trace_add("write", lambda *_: self._update_preview())

        ttk.Separator(frm).grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(btns, text="Cancel", bootstyle="secondary-outline", command=self.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="  Save Shift  ", bootstyle="primary", command=self._save).grid(row=0, column=1)

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent)
        self.grab_set()
        self.wait_visibility()
        self.focus_force()
        self.wait_window(self)

    def _update_preview(self):
        try:
            s, e = self.var_start.get().strip(), self.var_end.get().strip()
            if len(s) == 5 and len(e) == 5:
                hrs = shift_hours(s, e)
                cost = shift_cost(self._emp.wage, s, e)
                self.var_preview.set(f"{hrs:.1f} hrs  ·  {fmt_money(cost)} labor cost")
            else:
                self.var_preview.set("")
        except Exception:
            self.var_preview.set("")

    def _save(self):
        s, e = self.var_start.get().strip(), self.var_end.get().strip()
        if len(s) != 5 or ":" not in s or len(e) != 5 or ":" not in e:
            messagebox.showerror("Invalid", "Enter times in HH:MM format.", parent=self)
            return
        self.result = (s, e)
        self.destroy()


# ── Schedule Manager dialog ──────────────────────────────────
class ScheduleManagerDialog(tk.Toplevel):
    def __init__(self, parent: "ShiftPlannerApp"):
        super().__init__(parent)
        self.app = parent
        self.title("📅 Schedule Manager")
        self.geometry("1260x760")
        self.minsize(1040, 620)

        self._schedule_paths: List[str] = []

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        left = ttk.LabelFrame(outer, text="Saved Schedules", padding=12)
        left.pack(side="left", fill="y", padx=(0, 12))

        self.sched_listbox = tk.Listbox(
            left,
            height=20,
            width=35,
            font=("Segoe UI", 11),
            selectbackground="#0d6efd",
            selectforeground="white",
            activestyle="none",
            borderwidth=0,
            relief="flat",
        )
        self.sched_listbox.pack(fill="y", expand=True)
        self.sched_listbox.bind("<<ListboxSelect>>", lambda e: self._preview_selected())
        self.sched_listbox.bind("<Double-Button-1>", lambda e: self._load_into_planner())

        left_btns = ttk.Frame(left)
        left_btns.pack(fill="x", pady=(10, 0))
        ttk.Button(left_btns, text="Refresh", bootstyle="secondary", command=self._refresh).pack(side="left")
        ttk.Button(left_btns, text="Open →", bootstyle="primary", command=self._load_into_planner).pack(side="right")

        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(right)
        header.pack(fill="x")
        self.lbl_title = ttk.Label(header, text="No schedule selected", font=("Segoe UI", 13, "bold"))
        self.lbl_title.pack(side="left")

        actions = ttk.Frame(header)
        actions.pack(side="right")
        for txt, cmd, style in [
            ("💾 Save Current", self._save_current, "primary"),
            ("✏️ Rename", self._rename_selected, "warning-outline"),
            ("🗑 Delete", self._delete_selected, "danger-outline"),
            ("📤 Export CSV", self._export_csv, "info-outline"),
            ("Close", self.destroy, "primary"),
        ]:
            ttk.Button(actions, text=txt, bootstyle=style, command=cmd).pack(side="left", padx=4)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=(10, 0))

        table_box = ttk.LabelFrame(right, text="Schedule Contents", padding=10)
        table_box.pack(fill="both", expand=True, pady=(12, 0))

        cols = ("employee", "role", "wage", "max_hours", "mon", "tue", "wed", "thu", "fri", "sat", "sun", "total_hrs", "total_cost")
        self.tree = ttk.Treeview(table_box, columns=cols, show="headings", height=15)

        heads = [
            ("employee", "Employee", 140),
            ("role", "Role", 100),
            ("wage", "$/hr", 70),
            ("max_hours", "Max Hrs", 75),
            ("mon", "Mon", 65),
            ("tue", "Tue", 65),
            ("wed", "Wed", 65),
            ("thu", "Thu", 65),
            ("fri", "Fri", 65),
            ("sat", "Sat", 65),
            ("sun", "Sun", 65),
            ("total_hrs", "Total Hrs", 85),
            ("total_cost", "Total Cost", 90),
        ]
        for cid, ctext, cw in heads:
            self.tree.heading(cid, text=ctext)
            self.tree.column(cid, width=cw, anchor="w" if cid in ("employee", "role") else "center")

        vsb = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        kpi = ttk.LabelFrame(right, text="Week Summary", padding=12)
        kpi.pack(fill="x", pady=(10, 0))

        self.var_kpi_emps = tk.StringVar(value="—")
        self.var_kpi_shifts = tk.StringVar(value="—")
        self.var_kpi_hours = tk.StringVar(value="—")
        self.var_kpi_cost = tk.StringVar(value="—")
        self.var_kpi_revenue = tk.StringVar(value="—")
        self.var_kpi_pct = tk.StringVar(value="—")
        self.var_kpi_saved = tk.StringVar(value="—")

        kpis = [
            ("Employees", self.var_kpi_emps),
            ("Shifts", self.var_kpi_shifts),
            ("Total Hours", self.var_kpi_hours),
            ("Total Cost", self.var_kpi_cost),
            ("Projected Rev.", self.var_kpi_revenue),
            ("Labor %", self.var_kpi_pct),
            ("Saved", self.var_kpi_saved),
        ]
        for i, (lbl, var) in enumerate(kpis):
            ttk.Label(kpi, text=lbl, font=("Segoe UI", 9, "bold"), foreground=C_MUTED).grid(row=0, column=i, padx=14, sticky="w")
            ttk.Label(kpi, textvariable=var, font=("Segoe UI", 11, "bold")).grid(row=1, column=i, padx=14, sticky="w")

        self._refresh()
        self.transient(parent)
        self.grab_set()
        self.focus_force()

    def _refresh(self):
        self.sched_listbox.delete(0, "end")
        self._schedule_paths = list_saved_schedules()
        for p in self._schedule_paths:
            name = os.path.splitext(os.path.basename(p))[0].replace("_", " ")
            self.sched_listbox.insert("end", name)
        if self._schedule_paths:
            self.sched_listbox.selection_set(0)
            self._preview_selected()

    def _selected_path(self) -> Optional[str]:
        sel = self.sched_listbox.curselection()
        if not sel:
            return None
        return self._schedule_paths[int(sel[0])]

    def _preview_selected(self):
        path = self._selected_path()
        if not path:
            return
        try:
            rec = load_schedule_from_disk(path)
        except Exception as ex:
            self.lbl_title.config(text=f"Error loading: {ex}")
            return

        name = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
        self.lbl_title.config(text=f"{rec.name}  ·  {name}")

        for row in self.tree.get_children():
            self.tree.delete(row)

        total_cost = 0.0
        total_hours = 0.0
        for emp in rec.employees:
            row_vals = [emp.name, emp.role or "—", f"${emp.wage:.2f}", f"{emp.max_hours:.1f}"]
            emp_hrs = 0.0
            emp_cost = 0.0
            for di in range(7):
                key = f"{emp.emp_id}-{di}"
                s = rec.shifts.get(key)
                if s:
                    h = shift_hours(s.start, s.end)
                    row_vals.append(f"{h:.1f}h")
                    emp_hrs += h
                    emp_cost += emp.wage * h
                elif not emp.is_available(di):
                    row_vals.append("N/A")
                else:
                    row_vals.append("—")
            row_vals += [f"{emp_hrs:.1f}h", fmt_money(emp_cost)]
            total_hours += emp_hrs
            total_cost += emp_cost
            self.tree.insert("", "end", values=row_vals)

        rev = ffloat(rec.revenue)
        pct = (total_cost / rev * 100) if rev > 0 else None
        saved_at = rec.created_at[:10] if rec.created_at else "—"

        self.var_kpi_emps.set(str(len(rec.employees)))
        self.var_kpi_shifts.set(str(len(rec.shifts)))
        self.var_kpi_hours.set(f"{total_hours:.1f}h")
        self.var_kpi_cost.set(fmt_money(total_cost))
        self.var_kpi_revenue.set(fmt_money(rev) if rev > 0 else "—")
        self.var_kpi_pct.set(f"{pct:.1f}%" if pct is not None else "—")
        self.var_kpi_saved.set(saved_at)

    def _load_into_planner(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Select", "Select a schedule first.", parent=self)
            return
        try:
            rec = load_schedule_from_disk(path)
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to load:\n{ex}", parent=self)
            return
        self.app.load_schedule_record(rec)
        self.destroy()

    def _save_current(self):
        name = simpledialog.askstring(
            "Save Schedule",
            "Enter a name for this schedule:",
            initialvalue=self.app._current_schedule_name or f"Week of {week_monday(self.app.week_offset).strftime('%b %d %Y')}",
            parent=self,
        )
        if not name:
            return
        name = name.strip()
        path = make_schedule_path(name)
        if os.path.exists(path):
            if not messagebox.askyesno("Overwrite", f"'{name}' already exists. Overwrite it?", parent=self):
                return
        rec = self.app.build_schedule_record(name)
        save_schedule_to_disk(path, rec)
        self.app._current_schedule_name = name
        self._refresh()
        messagebox.showinfo("Saved", f"Schedule '{name}' saved.", parent=self)

    def _rename_selected(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Select", "Select a schedule first.", parent=self)
            return
        old_name = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=old_name, parent=self)
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        new_path = make_schedule_path(new_name)
        if os.path.exists(new_path) and new_path != path:
            if not messagebox.askyesno("Overwrite", f"'{new_name}' already exists. Overwrite?", parent=self):
                return
        try:
            rec = load_schedule_from_disk(path)
            rec.name = new_name
            save_schedule_to_disk(new_path, rec)
            if new_path != path:
                os.remove(path)
        except Exception as ex:
            messagebox.showerror("Error", f"Rename failed:\n{ex}", parent=self)
            return
        self._refresh()

    def _delete_selected(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Select", "Select a schedule first.", parent=self)
            return
        name = os.path.splitext(os.path.basename(path))[0].replace("_", " ")
        if not messagebox.askyesno("Delete", f"Permanently delete '{name}'?\nThis cannot be undone.", parent=self):
            return
        try:
            os.remove(path)
        except Exception as ex:
            messagebox.showerror("Error", f"Delete failed:\n{ex}", parent=self)
            return
        self._refresh()
        self.lbl_title.config(text="No schedule selected")
        for row in self.tree.get_children():
            self.tree.delete(row)

    def _export_csv(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Select", "Select a schedule first.", parent=self)
            return
        try:
            rec = load_schedule_from_disk(path)
        except Exception as ex:
            messagebox.showerror("Error", f"Could not load:\n{ex}", parent=self)
            return

        out = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=safe_name(rec.name) + ".csv",
            filetypes=[("CSV", "*.csv")],
            title="Export Schedule CSV",
            parent=self,
        )
        if not out:
            return

        rows = []
        for shift in sorted(rec.shifts.values(), key=lambda s: (s.day_idx, s.emp_id)):
            emp = next((e for e in rec.employees if e.emp_id == shift.emp_id), None)
            if not emp:
                continue
            hrs = shift_hours(shift.start, shift.end)
            cost = shift_cost(emp.wage, shift.start, shift.end)
            rows.append(
                {
                    "Day": DAYS[shift.day_idx],
                    "Employee": emp.name,
                    "Role": emp.role,
                    "Wage ($/hr)": f"{emp.wage:.2f}",
                    "Max Hours": f"{emp.max_hours:.2f}",
                    "Start": shift.start,
                    "End": shift.end,
                    "Hours": f"{hrs:.2f}",
                    "Labor Cost": f"{cost:.2f}",
                }
            )

        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else ["Day"])
            writer.writeheader()
            writer.writerows(rows)
            if rows:
                total = sum(float(r["Labor Cost"]) for r in rows)
                f.write(f"\n,,,,,,,TOTAL,{total:.2f}\n")

        messagebox.showinfo("Exported", f"Exported to:\n{out}", parent=self)


# ── Stat card ────────────────────────────────────────────────
class StatCard(ttk.Frame):
    def __init__(self, parent, title, value="$0.00", value_color=C_TEXT, **kw):
        super().__init__(parent, **kw)
        inner = ttk.Frame(self, padding=(14, 10))
        inner.pack(fill="both", expand=True)
        ttk.Label(inner, text=title.upper(), font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w")
        self.var_value = tk.StringVar(value=value)
        self.lbl = ttk.Label(inner, textvariable=self.var_value, font=("Segoe UI", 18, "bold"), foreground=value_color)
        self.lbl.pack(anchor="w", pady=(4, 0))

    def set(self, val, color=None):
        self.var_value.set(val)
        if color:
            self.lbl.configure(foreground=color)


# ── Main application ─────────────────────────────────────────
class ShiftPlannerApp(tb.Window):
    def __init__(self):
        super().__init__(themename=THEME)
        self.title(APP_TITLE)
        self.geometry("1320x860")
        self.minsize(1040, 720)

        self.employees: List[Employee] = []
        self.shifts: Dict[str, Shift] = {}
        self.week_offset = 0
        self._current_schedule_name: Optional[str] = None
        self._grid_scroll_x = 0.0
        self._grid_scroll_y = 0.0

        try:
            self.employees = load_employees_from_disk()
        except Exception:
            self.employees = []

        self._build_ui()
        self._render()

    # ── Build UI ─────────────────────────────────────────────
    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(12, 8))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=APP_TITLE, font=("Segoe UI", 14, "bold"), foreground=C_GOLD).pack(side="left")
        ttk.Label(toolbar, text=" — Faraj Software Solutions", font=("Segoe UI", 10), foreground=C_MUTED).pack(side="left")

        for txt, cmd, sty in [
            ("📅 Schedule Manager", self._open_schedule_manager, "primary"),
            ("💾 Save Schedule", self._quick_save, "success"),
            ("Export CSV", self._export_csv, "secondary"),
            ("🗑 Clear Week", self._clear_week, "danger"),
        ]:
            ttk.Button(toolbar, text=txt, bootstyle=sty, command=cmd).pack(side="right", padx=4)

        self.var_sched_label = tk.StringVar(value="No schedule loaded")
        ttk.Label(toolbar, textvariable=self.var_sched_label, font=("Segoe UI", 9, "italic"), foreground=C_MUTED).pack(side="right", padx=12)

        ttk.Separator(self).pack(fill="x")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)

        self._build_week_nav(main)
        self._build_stats_bar(main)
        self._build_schedule(main)
        self._build_suggestions(main)

    def _build_sidebar(self, parent):
        sb = ttk.Frame(parent, width=360)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        ttk.Separator(parent, orient="vertical").pack(side="left", fill="y")

        canvas_wrap = ttk.Frame(sb)
        canvas_wrap.pack(fill="both", expand=True)

        sidebar_vsb = ttk.Scrollbar(canvas_wrap, orient="vertical")
        sidebar_vsb.pack(side="right", fill="y")

        self.sidebar_canvas = tk.Canvas(
            canvas_wrap,
            yscrollcommand=sidebar_vsb.set,
            highlightthickness=0,
            bg=C_BG,
        )
        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_vsb.configure(command=self.sidebar_canvas.yview)

        self.sidebar_inner = ttk.Frame(self.sidebar_canvas, padding=(14, 12))
        self.sidebar_win = self.sidebar_canvas.create_window((0, 0), window=self.sidebar_inner, anchor="nw")

        self.sidebar_inner.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        )
        self.sidebar_canvas.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.itemconfig(self.sidebar_win, width=e.width)
        )

        def _sidebar_mousewheel(event):
            self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.sidebar_canvas.bind("<MouseWheel>", _sidebar_mousewheel)
        self.sidebar_inner.bind("<MouseWheel>", _sidebar_mousewheel)

        ttk.Label(self.sidebar_inner, text="ADD EMPLOYEE", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w", pady=(0, 6))

        frm = ttk.LabelFrame(self.sidebar_inner, text="", padding=10)
        frm.pack(fill="x")
        self.var_emp_name = tk.StringVar()
        self.var_emp_role = tk.StringVar()
        self.var_emp_wage = tk.StringVar()
        self.var_emp_max_hours = tk.StringVar(value="40")
        for label, var in [
            ("Name", self.var_emp_name),
            ("Role", self.var_emp_role),
            ("Wage ($/hr)", self.var_emp_wage),
            ("Max Weekly Hours", self.var_emp_max_hours),
        ]:
            ttk.Label(frm, text=label, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 2))
            entry = ttk.Entry(frm, textvariable=var)
            entry.pack(fill="x")
            entry.bind("<MouseWheel>", _sidebar_mousewheel)
        ttk.Button(frm, text="＋ Add Employee", bootstyle="primary", command=self._add_employee_quick).pack(fill="x", pady=(10, 0))

        ttk.Label(self.sidebar_inner, text="EMPLOYEES", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w", pady=(14, 6))
        employees_box = ttk.Frame(self.sidebar_inner)
        employees_box.pack(fill="x")
        self.emp_inner = ttk.Frame(employees_box)
        self.emp_inner.pack(fill="x")

        ttk.Separator(self.sidebar_inner).pack(fill="x", pady=10)
        ttk.Label(self.sidebar_inner, text="PROJECTED REVENUE", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w", pady=(0, 6))

        self.var_use_weekly_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.sidebar_inner,
            text="Use weekly revenue only (skip daily breakdown)",
            variable=self.var_use_weekly_only,
            bootstyle="round-toggle",
            command=self._on_revenue_mode_toggle,
        ).pack(anchor="w", pady=(0, 8))

        self.day_revenue_vars = [tk.StringVar() for _ in range(7)]
        self.day_rev_frame = ttk.Frame(self.sidebar_inner)
        self.day_rev_frame.pack(fill="x")

        for i, day in enumerate(DAYS):
            row = ttk.Frame(self.day_rev_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=day, width=5).pack(side="left")
            ttk.Label(row, text="$ ").pack(side="left", padx=(0, 3))
            ent = ttk.Entry(row, textvariable=self.day_revenue_vars[i], width=18)
            ent.pack(side="left", fill="x", expand=True)
            ent.bind("<KeyRelease>", lambda e: self._on_revenue_change())
            ent.bind("<FocusOut>", lambda e: self._on_revenue_change())
            ent.bind("<MouseWheel>", _sidebar_mousewheel)

        weekly_row = ttk.Frame(self.sidebar_inner)
        weekly_row.pack(fill="x", pady=(8, 0))
        ttk.Label(weekly_row, text="Weekly", width=5, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(weekly_row, text="$ ").pack(side="left", padx=(0, 3))

        self.var_revenue = tk.StringVar()
        self.rev_entry = ttk.Entry(weekly_row, textvariable=self.var_revenue)
        self.rev_entry.pack(side="left", fill="x", expand=True)
        self.rev_entry.bind("<KeyRelease>", lambda e: self._sync_weekly_to_daily_from_weekly())
        self.rev_entry.bind("<FocusOut>", lambda e: self._sync_weekly_to_daily_from_weekly())
        self.rev_entry.bind("<MouseWheel>", _sidebar_mousewheel)

        ttk.Separator(self.sidebar_inner).pack(fill="x", pady=10)
        ttk.Label(self.sidebar_inner, text="COVERAGE TARGETS", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w", pady=(0, 6))
        ttk.Label(self.sidebar_inner, text="Minimum staff needed per day", font=("Segoe UI", 9), foreground=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.coverage_vars = [tk.StringVar() for _ in range(7)]
        coverage_frame = ttk.Frame(self.sidebar_inner)
        coverage_frame.pack(fill="x")
        for i, day in enumerate(DAYS):
            row = ttk.Frame(coverage_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text=day, width=5).pack(side="left")
            ent = ttk.Entry(row, textvariable=self.coverage_vars[i], width=10)
            ent.pack(side="left", fill="x", expand=True)
            ent.bind("<KeyRelease>", lambda e: self._refresh_stats())
            ent.bind("<MouseWheel>", _sidebar_mousewheel)

        self.var_labor_pct = tk.StringVar(value="—")
        self.lbl_labor_pct = ttk.Label(self.sidebar_inner, textvariable=self.var_labor_pct, font=("Segoe UI", 22, "bold"), foreground=C_MUTED, anchor="center")
        self.lbl_labor_pct.pack(fill="x", pady=(14, 2))
        ttk.Label(self.sidebar_inner, text="LABOR % OF WEEKLY REVENUE", font=("Segoe UI", 8, "bold"), foreground=C_MUTED, anchor="center").pack()

    def _build_week_nav(self, parent):
        nav = ttk.Frame(parent, padding=(12, 8))
        nav.pack(fill="x")
        ttk.Button(nav, text="‹", bootstyle="warning", width=3, command=lambda: self._change_week(-1)).pack(side="left")
        self.var_week_label = tk.StringVar()
        ttk.Label(nav, textvariable=self.var_week_label, font=("Segoe UI", 13, "bold")).pack(side="left", padx=16)
        ttk.Button(nav, text="›", bootstyle="warning", width=3, command=lambda: self._change_week(1)).pack(side="left")
        ttk.Button(nav, text="Today", bootstyle="link", command=self._goto_today).pack(side="left", padx=8)

    def _build_stats_bar(self, parent):
        bar = ttk.Frame(parent, padding=(12, 4))
        bar.pack(fill="x")
        ttk.Separator(parent).pack(fill="x")
        self.stat_total = StatCard(bar, "Total Labor Cost", value_color=C_TEAL)
        self.stat_hours = StatCard(bar, "Total Hours")
        self.stat_avg_day = StatCard(bar, "Avg Cost / Day")
        self.stat_peak = StatCard(bar, "Highest Day", value_color=C_ORANGE)
        self.stat_shifts = StatCard(bar, "Shifts Scheduled")
        self.stat_over = StatCard(bar, "Over Budget Days", value_color=C_RED)
        for c in (self.stat_total, self.stat_hours, self.stat_avg_day, self.stat_peak, self.stat_shifts, self.stat_over):
            c.pack(side="left", fill="both", expand=True, padx=3, pady=4)
        ttk.Separator(parent).pack(fill="x")

    def _build_schedule(self, parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        xsb = ttk.Scrollbar(wrap, orient="horizontal")
        xsb.pack(side="bottom", fill="x")
        ysb = ttk.Scrollbar(wrap, orient="vertical")
        ysb.pack(side="right", fill="y")
        self.grid_canvas = tk.Canvas(wrap, xscrollcommand=xsb.set, yscrollcommand=ysb.set, highlightthickness=0, bg=C_BG)
        self.grid_canvas.pack(side="left", fill="both", expand=True)
        xsb.configure(command=self.grid_canvas.xview)
        ysb.configure(command=self.grid_canvas.yview)
        self.grid_inner = ttk.Frame(self.grid_canvas)
        self.grid_win = self.grid_canvas.create_window((0, 0), window=self.grid_inner, anchor="nw")
        self.grid_inner.bind("<Configure>", lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all")))
        self.grid_canvas.bind("<Configure>", lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all")))
        self.grid_canvas.bind("<MouseWheel>", lambda e: self.grid_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.grid_canvas.bind("<Shift-MouseWheel>", lambda e: self.grid_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _build_suggestions(self, parent):
        ttk.Separator(parent).pack(fill="x")
        outer = ttk.Frame(parent, padding=(12, 4))
        outer.pack(fill="x", expand=False)
        ttk.Label(outer, text="💡 SUGGESTIONS", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="w", pady=(0, 4))
        self.sugg_frame = ttk.Frame(outer)
        self.sugg_frame.pack(fill="x", expand=True)

    # ── Revenue helpers ──────────────────────────────────────
    def _daily_revenue_numbers(self) -> List[float]:
        if self.var_use_weekly_only.get():
            return [0.0] * 7
        return [ffloat(v.get()) for v in self.day_revenue_vars]

    def _effective_day_revenue_numbers(self) -> List[float]:
        if self.var_use_weekly_only.get():
            weekly = ffloat(self.var_revenue.get())
            return [weekly / 7.0] * 7 if weekly > 0 else [0.0] * 7
        return [ffloat(v.get()) for v in self.day_revenue_vars]

    def _weekly_revenue_value(self) -> float:
        if self.var_use_weekly_only.get():
            return ffloat(self.var_revenue.get())
        daily_total = sum(self._daily_revenue_numbers())
        weekly_manual = ffloat(self.var_revenue.get())
        return daily_total if daily_total > 0 else weekly_manual

    def _on_revenue_mode_toggle(self):
        weekly_only = self.var_use_weekly_only.get()
        state = "disabled" if weekly_only else "normal"
        for child in self.day_rev_frame.winfo_children():
            for grandchild in child.winfo_children():
                if isinstance(grandchild, ttk.Entry):
                    grandchild.configure(state=state)
        if weekly_only:
            for var in self.day_revenue_vars:
                var.set("")
        self._refresh_stats()
        self._render_grid()

    def _on_revenue_change(self):
        if not self.var_use_weekly_only.get():
            daily_total = sum(self._daily_revenue_numbers())
            if daily_total > 0:
                self.var_revenue.set(f"{daily_total:.2f}")
            elif self.var_revenue.get().strip():
                self.var_revenue.set("")
        self._refresh_stats()
        self._render_grid()

    def _sync_weekly_to_daily_from_weekly(self):
        self._refresh_stats()
        self._render_grid()

    def _capture_grid_scroll(self):
        if hasattr(self, "grid_canvas"):
            try:
                self._grid_scroll_x = self.grid_canvas.xview()[0]
                self._grid_scroll_y = self.grid_canvas.yview()[0]
            except Exception:
                self._grid_scroll_x = 0.0
                self._grid_scroll_y = 0.0

    def _restore_grid_scroll(self):
        if hasattr(self, "grid_canvas"):
            try:
                self.grid_canvas.update_idletasks()
                self.grid_canvas.xview_moveto(self._grid_scroll_x)
                self.grid_canvas.yview_moveto(self._grid_scroll_y)
            except Exception:
                pass

    # ── Render ───────────────────────────────────────────────
    def _render(self):
        self._render_employees()
        self._render_grid()
        self._refresh_stats()
        self._update_week_label()

    def _update_week_label(self):
        mon = week_monday(self.week_offset)
        sun = mon + timedelta(days=6)
        self.var_week_label.set(f"Week of {mon.strftime('%b %d')} – {sun.strftime('%b %d, %Y')}")

    def _render_employees(self):
        for w in self.emp_inner.winfo_children():
            w.destroy()
        if not self.employees:
            ttk.Label(self.emp_inner, text="No employees yet.", font=("Segoe UI", 10), foreground=C_MUTED).pack(anchor="w", pady=8)
            return
        for emp in self.employees:
            c = emp.color()
            card = ttk.Frame(self.emp_inner, padding=(8, 6))
            card.pack(fill="x", pady=2)

            ttk.Label(card, text=emp.initials(), font=("Segoe UI", 11, "bold"), foreground=c["fg"], background=c["bg"], width=3, anchor="center").pack(side="left", padx=(0, 8))

            info = ttk.Frame(card)
            info.pack(side="left", fill="x", expand=True)
            ttk.Label(info, text=emp.name, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            ttk.Label(info, text=f"{emp.role or 'Staff'}  ·  ${emp.wage:.2f}/hr  ·  Max {emp.max_hours:.0f}h", font=("Segoe UI", 9), foreground=C_MUTED).pack(anchor="w")

            if emp.unavailable_days:
                unavailable_text = ", ".join(DAYS[i] for i in emp.unavailable_days)
                ttk.Label(info, text=f"Unavailable: {unavailable_text}", font=("Segoe UI", 8), foreground=C_ORANGE).pack(anchor="w")

            wk_cost = sum(shift_cost(emp.wage, s.start, s.end) for s in self.shifts.values() if s.emp_id == emp.emp_id)
            if wk_cost > 0:
                emp_hours = sum(shift_hours(s.start, s.end) for s in self.shifts.values() if s.emp_id == emp.emp_id)
                fg = C_RED if emp_hours > emp.max_hours else C_TEAL
                ttk.Label(info, text=f"{fmt_money(wk_cost)}  ·  {emp_hours:.1f}h", font=("Segoe UI", 9, "bold"), foreground=fg).pack(anchor="w")

            bf = ttk.Frame(card)
            bf.pack(side="right", padx=(5, 0))
            ttk.Button(bf, text="✏️", bootstyle="secondary", width=3, command=lambda e=emp: self._edit_employee(e)).pack(side="left", padx=2)
            ttk.Button(bf, text="🗑️", bootstyle="danger", width=3, command=lambda e=emp: self._delete_employee(e)).pack(side="left", padx=2)

    def _render_grid(self):
        self._capture_grid_scroll()
        for w in self.grid_inner.winfo_children():
            w.destroy()
        mon = week_monday(self.week_offset)
        today = date.today()
        day_costs = self._compute_day_costs()
        day_revenue = self._effective_day_revenue_numbers()
        day_staff_counts = self._compute_day_staff_counts()

        corner = ttk.Frame(self.grid_inner, padding=(6, 4), width=190)
        corner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        corner.grid_propagate(False)
        ttk.Label(corner, text="EMPLOYEE", font=("Segoe UI", 8, "bold"), foreground=C_MUTED).pack(anchor="center")

        for di in range(7):
            d = mon + timedelta(days=di)
            hit = d == today
            hdr = ttk.Frame(self.grid_inner, padding=(4, 6), width=142)
            hdr.grid(row=0, column=di + 1, sticky="nsew", padx=1, pady=1)
            hdr.grid_propagate(False)
            ttk.Label(hdr, text=DAYS[di].upper(), font=("Segoe UI", 8, "bold"), foreground=C_GOLD if hit else C_MUTED).pack()
            ttk.Label(hdr, text=str(d.day), font=("Segoe UI", 14, "bold"), foreground=C_GOLD if hit else C_TEXT).pack()
            if day_costs[di] > 0:
                ttk.Label(hdr, text=fmt_money(day_costs[di]), font=("Segoe UI", 9, "bold"), foreground=C_TEAL).pack()

            rev = day_revenue[di]
            if rev > 0:
                pct = day_costs[di] / rev * 100 if rev else 0
                pct_color = C_GREEN if pct < 25 else C_ORANGE if pct < 35 else C_RED
                pct_text = f"{pct:.0f}% labor"
                if self.var_use_weekly_only.get():
                    pct_text += " est."
                ttk.Label(hdr, text=pct_text, font=("Segoe UI", 8, "bold"), foreground=pct_color).pack()

            target = int(ffloat(self.coverage_vars[di].get(), 0))
            if target > 0:
                staff_ct = day_staff_counts[di]
                fg = C_GREEN if staff_ct >= target else C_RED
                ttk.Label(hdr, text=f"{staff_ct}/{target} staff", font=("Segoe UI", 8), foreground=fg).pack()

        ttk.Separator(self.grid_inner, orient="horizontal").grid(row=1, column=0, columnspan=8, sticky="ew")

        if not self.employees:
            ttk.Label(self.grid_inner, text="Add employees to start scheduling.", font=("Segoe UI", 11), foreground=C_MUTED).grid(row=2, column=0, columnspan=8, pady=40)
            self.after_idle(self._restore_grid_scroll)
            return

        for ri, emp in enumerate(self.employees):
            c = emp.color()
            row = ri + 2

            lf = ttk.Frame(self.grid_inner, padding=(6, 4), width=190)
            lf.grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
            lf.grid_propagate(False)
            ttk.Label(lf, text=emp.initials(), font=("Segoe UI", 11, "bold"), foreground=c["fg"], background=c["bg"], width=3, anchor="center").pack(side="left", padx=(0, 6))
            il = ttk.Frame(lf)
            il.pack(side="left")
            ttk.Label(il, text=emp.name, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            ttk.Label(il, text=emp.role or "Staff", font=("Segoe UI", 8), foreground=C_MUTED).pack(anchor="w")
            emp_hrs = sum(shift_hours(s.start, s.end) for s in self.shifts.values() if s.emp_id == emp.emp_id)
            if emp_hrs > 0:
                fg = C_RED if emp_hrs > emp.max_hours else C_TEAL
                ttk.Label(il, text=f"{emp_hrs:.1f}h / {emp.max_hours:.1f}h  ·  {fmt_money(emp_hrs * emp.wage)}", font=("Segoe UI", 8), foreground=fg).pack(anchor="w")
            elif emp.unavailable_days:
                ttk.Label(il, text="Unavailable some days", font=("Segoe UI", 8), foreground=C_ORANGE).pack(anchor="w")

            for di in range(7):
                key = f"{emp.emp_id}-{di}"
                shift = self.shifts.get(key)
                cell = ttk.Frame(self.grid_inner, padding=4, width=142)
                cell.grid(row=row, column=di + 1, sticky="nsew", padx=1, pady=1)
                cell.grid_propagate(False)
                if shift:
                    self._build_shift_block(cell, emp, shift, di)
                else:
                    if emp.is_available(di):
                        self._build_empty_cell(cell, emp, di)
                    else:
                        self._build_unavailable_cell(cell)

        self.grid_inner.grid_columnconfigure(0, minsize=190)
        for di in range(7):
            self.grid_inner.grid_columnconfigure(di + 1, minsize=142)

        self.after_idle(self._restore_grid_scroll)

    def _build_shift_block(self, parent, emp, shift, di):
        c = emp.color()
        block = tk.Frame(parent, bg=c["bg"], highlightbackground=c["fg"], highlightthickness=1, cursor="hand2")
        block.pack(fill="both", expand=True, padx=2, pady=2)
        hrs = shift_hours(shift.start, shift.end)
        cost = shift_cost(emp.wage, shift.start, shift.end)
        tk.Label(block, text=f"{shift.start}–{shift.end}", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["bg"]).pack(anchor="w", padx=6, pady=(6, 0))
        tk.Label(block, text=f"{hrs:.1f}h", font=("Segoe UI", 11, "bold"), fg=c["fg"], bg=c["bg"]).pack(anchor="w", padx=6)
        tk.Label(block, text=fmt_money(cost), font=("Segoe UI", 9), fg=c["fg"], bg=c["bg"]).pack(anchor="w", padx=6, pady=(0, 4))
        tk.Button(
            block,
            text="✕",
            font=("Segoe UI", 8, "bold"),
            fg="#fff",
            bg=c["bg"],
            activebackground=C_RED,
            relief="flat",
            cursor="hand2",
            command=lambda: self._delete_shift(emp.emp_id, di),
        ).place(relx=1.0, rely=0.0, anchor="ne", x=-2, y=2)
        for w in [block] + block.winfo_children():
            if not isinstance(w, tk.Button):
                w.bind("<Button-1>", lambda e, ei=emp.emp_id, d=di: self._open_shift(ei, d))

    def _build_empty_cell(self, parent, emp, di):
        ttk.Button(parent, text="+", bootstyle="secondary-outline", command=lambda: self._open_shift(emp.emp_id, di)).pack(fill="both", expand=True, padx=4, pady=4)

    def _build_unavailable_cell(self, parent):
        lbl = ttk.Label(parent, text="Unavailable", anchor="center", foreground=C_ORANGE, font=("Segoe UI", 9, "bold"))
        lbl.pack(fill="both", expand=True, padx=4, pady=4)

    # ── Stats ────────────────────────────────────────────────
    def _compute_day_costs(self):
        day_costs = [0.0] * 7
        for s in self.shifts.values():
            emp = self._get_emp(s.emp_id)
            if emp:
                day_costs[s.day_idx] += shift_cost(emp.wage, s.start, s.end)
        return day_costs

    def _compute_day_staff_counts(self):
        counts = [0] * 7
        for s in self.shifts.values():
            counts[s.day_idx] += 1
        return counts

    def _refresh_stats(self):
        day_costs = self._compute_day_costs()
        total_cost = sum(day_costs)
        total_hours = sum(shift_hours(s.start, s.end) for s in self.shifts.values())
        total_shifts = len(self.shifts)
        weekly_revenue = self._weekly_revenue_value()
        day_revenue = self._effective_day_revenue_numbers()

        self.stat_total.set(fmt_money(total_cost), color=C_TEAL)
        self.stat_hours.set(f"{total_hours:.1f}h")
        self.stat_avg_day.set(fmt_money(total_cost / 7 if total_cost else 0))
        self.stat_shifts.set(str(total_shifts))

        if total_cost > 0:
            pi = day_costs.index(max(day_costs))
            peak_color = C_ORANGE if day_costs[pi] > (total_cost / 7) * 1.5 else C_TEXT
            self.stat_peak.set(f"{DAYS[pi]} {fmt_money(day_costs[pi])}", color=peak_color)
        else:
            self.stat_peak.set("—")

        over_budget_days = 0
        for di in range(7):
            rev = day_revenue[di]
            if rev > 0 and day_costs[di] / rev * 100 > 35:
                over_budget_days += 1
        self.stat_over.set(str(over_budget_days), color=C_RED if over_budget_days else C_GREEN)

        if weekly_revenue > 0:
            pct = total_cost / weekly_revenue * 100
            self.var_labor_pct.set(f"{pct:.1f}%")
            self.lbl_labor_pct.configure(foreground=C_GREEN if pct < 25 else C_ORANGE if pct < 35 else C_RED)
        else:
            self.var_labor_pct.set("—")
            self.lbl_labor_pct.configure(foreground=C_MUTED)

        self._update_suggestions(day_costs, total_cost)

    def _update_suggestions(self, day_costs, total_cost):
        for w in self.sugg_frame.winfo_children():
            w.destroy()

        tips = []

        if not self.employees:
            ttk.Label(self.sugg_frame, text="Add employees and shifts to see suggestions.", font=("Segoe UI", 9), foreground=C_MUTED).pack(side="left")
            return

        day_revenue = self._effective_day_revenue_numbers()
        day_staff_counts = self._compute_day_staff_counts()

        for emp in self.employees:
            days_on = sum(1 for di in range(7) if f"{emp.emp_id}-{di}" in self.shifts)
            if days_on == 7:
                tips.append(f"📅 {emp.name} is scheduled all 7 days — consider a rest day")

            emp_hrs = sum(
                shift_hours(self.shifts[f"{emp.emp_id}-{di}"].start, self.shifts[f"{emp.emp_id}-{di}"].end)
                for di in range(7)
                if f"{emp.emp_id}-{di}" in self.shifts
            )
            if emp_hrs > emp.max_hours:
                tips.append(f"🕐 {emp.name} is at {emp_hrs:.1f}h — over max of {emp.max_hours:.1f}h")
            elif emp_hrs > emp.max_hours * 0.9:
                tips.append(f"⚠️ {emp.name} is near max hours at {emp_hrs:.1f}h")

            for di in emp.unavailable_days:
                if f"{emp.emp_id}-{di}" in self.shifts:
                    tips.append(f"🚫 {emp.name} is scheduled on unavailable day {DAYS[di]}")

        weekly_revenue = self._weekly_revenue_value()
        if weekly_revenue > 0 and total_cost > 0:
            pct = total_cost / weekly_revenue * 100
            if pct > 35:
                tips.append(f"⚠️ Labor is {pct:.1f}% of weekly revenue — target is 25–30%")
            elif pct < 15:
                tips.append(f"✅ Labor at {pct:.1f}% — well within target")

        for di in range(7):
            rev = day_revenue[di]
            if rev > 0 and day_costs[di] > 0:
                pct = day_costs[di] / rev * 100
                suffix = " est." if self.var_use_weekly_only.get() else ""
                if self.var_use_weekly_only.get():
                    tips.append(f"💸 {DAYS[di]} labor is {pct:.1f}% of revenue{suffix}")
                elif pct > 35:
                    tips.append(f"💸 {DAYS[di]} is at {pct:.1f}% labor vs revenue")

            target = int(ffloat(self.coverage_vars[di].get(), 0))
            staff_ct = day_staff_counts[di]
            if target > 0 and staff_ct < target:
                tips.append(f"👥 {DAYS[di]} is understaffed ({staff_ct}/{target})")
            elif target > 0 and staff_ct > target:
                tips.append(f"📉 {DAYS[di]} is over target staffing ({staff_ct}/{target})")

        if not tips:
            tips = ["✅ Schedule looks balanced. No major warnings."]

        seen = set()
        compact_tips = []
        for tip in tips:
            if tip not in seen:
                seen.add(tip)
                compact_tips.append(tip)

        for tip in compact_tips[:6]:
            pill = ttk.Label(
                self.sugg_frame,
                text=tip,
                font=("Segoe UI", 8),
                foreground=C_TEXT,
                padding=(8, 3),
            )
            pill.pack(side="left", padx=3, pady=2)

    def _cheapest_available_employee(self, day_idx: int) -> Optional[Employee]:
        available = [e for e in self.employees if e.is_available(day_idx)]
        if not available:
            return None
        return min(available, key=lambda e: e.wage)

    # ── Employee actions ─────────────────────────────────────
    def _add_employee_quick(self):
        name = self.var_emp_name.get().strip()
        wage = ffloat(self.var_emp_wage.get())
        max_hours = ffloat(self.var_emp_max_hours.get(), 40.0)
        if not name:
            messagebox.showerror("Missing", "Name is required.")
            return
        if wage <= 0:
            messagebox.showerror("Invalid", "Enter a valid hourly wage.")
            return
        if max_hours <= 0:
            messagebox.showerror("Invalid", "Enter a valid max weekly hours.")
            return
        emp = Employee(name, self.var_emp_role.get().strip(), wage, color_idx=len(self.employees), max_hours=max_hours)
        self.employees.append(emp)
        self.var_emp_name.set("")
        self.var_emp_role.set("")
        self.var_emp_wage.set("")
        self.var_emp_max_hours.set("40")
        save_employees_to_disk(self.employees)
        self._render()

    def _edit_employee(self, emp):
        dlg = EmployeeDialog(self, initial=emp)
        if dlg.result:
            emp.name = dlg.result.name
            emp.role = dlg.result.role
            emp.wage = dlg.result.wage
            emp.max_hours = dlg.result.max_hours
            emp.unavailable_days = dlg.result.unavailable_days
            save_employees_to_disk(self.employees)
            self._render()

    def _delete_employee(self, emp):
        if not messagebox.askyesno("Remove", f"Remove {emp.name} and all their shifts?"):
            return
        self.employees = [e for e in self.employees if e.emp_id != emp.emp_id]
        self.shifts = {k: v for k, v in self.shifts.items() if v.emp_id != emp.emp_id}
        save_employees_to_disk(self.employees)
        self._render()

    def _get_emp(self, emp_id):
        return next((e for e in self.employees if e.emp_id == emp_id), None)

    # ── Shift actions ────────────────────────────────────────
    def _open_shift(self, emp_id, day_idx):
        emp = self._get_emp(emp_id)
        if not emp:
            return
        if not emp.is_available(day_idx):
            messagebox.showwarning("Unavailable", f"{emp.name} is marked unavailable on {DAYS[day_idx]}.")
            return

        mon = week_monday(self.week_offset)
        d = mon + timedelta(days=day_idx)
        key = f"{emp_id}-{day_idx}"
        dlg = ShiftDialog(self, emp, f"{DAYS[day_idx]}, {d.strftime('%b %d')}", initial=self.shifts.get(key))
        if dlg.result:
            s, e = dlg.result
            proposed_hours = shift_hours(s, e)
            existing_emp_hours = sum(
                shift_hours(v.start, v.end)
                for k, v in self.shifts.items()
                if v.emp_id == emp_id and k != key
            )
            if existing_emp_hours + proposed_hours > emp.max_hours + 0.01:
                if not messagebox.askyesno(
                    "Max Hours Warning",
                    f"This shift puts {emp.name} at {existing_emp_hours + proposed_hours:.1f}h "
                    f"for the week, over their max of {emp.max_hours:.1f}h.\n\nSave anyway?",
                ):
                    return
            self.shifts[key] = Shift(emp_id, day_idx, s, e)
            self._render()

    def _delete_shift(self, emp_id, day_idx):
        key = f"{emp_id}-{day_idx}"
        if key in self.shifts:
            del self.shifts[key]
            self._render()

    # ── Week navigation ──────────────────────────────────────
    def _change_week(self, delta):
        self.week_offset += delta
        self._render()

    def _goto_today(self):
        self.week_offset = 0
        self._render()

    # ── Schedule Manager ─────────────────────────────────────
    def _open_schedule_manager(self):
        ScheduleManagerDialog(self)

    def build_schedule_record(self, name: str) -> ScheduleRecord:
        mon = week_monday(self.week_offset)
        sun = mon + timedelta(days=6)
        week_label = f"Week of {mon.strftime('%b %d')} – {sun.strftime('%b %d, %Y')}"
        return ScheduleRecord(
            name=name,
            employees=[
                Employee(
                    e.name,
                    e.role,
                    e.wage,
                    emp_id=e.emp_id,
                    color_idx=e.color_idx,
                    max_hours=e.max_hours,
                    unavailable_days=list(e.unavailable_days),
                )
                for e in self.employees
            ],
            shifts=dict(self.shifts),
            revenue=self.var_revenue.get(),
            daily_revenue=[v.get() for v in self.day_revenue_vars],
            coverage_targets=[v.get() for v in self.coverage_vars],
            revenue_mode="weekly" if self.var_use_weekly_only.get() else "daily",
            week_label=week_label,
        )

    def load_schedule_record(self, rec: ScheduleRecord):
        self.employees = rec.employees
        if self.employees:
            Employee._counter = max(e.emp_id for e in self.employees)
        self.shifts = dict(rec.shifts)

        self.var_revenue.set(rec.revenue)
        self.var_use_weekly_only.set(getattr(rec, "revenue_mode", "daily") == "weekly")
        for i in range(7):
            self.day_revenue_vars[i].set(rec.daily_revenue[i] if i < len(rec.daily_revenue) else "")
            self.coverage_vars[i].set(rec.coverage_targets[i] if i < len(rec.coverage_targets) else "")

        self._current_schedule_name = rec.name
        self.var_sched_label.set(f"Loaded: {rec.name}")
        self._on_revenue_mode_toggle()
        self._render()

    def _quick_save(self):
        name = self._current_schedule_name
        if not name:
            name = simpledialog.askstring(
                "Save Schedule",
                "Enter a name for this schedule:",
                initialvalue=f"Week of {week_monday(self.week_offset).strftime('%b %d %Y')}",
                parent=self,
            )
        if not name:
            return
        name = name.strip()
        path = make_schedule_path(name)
        rec = self.build_schedule_record(name)
        save_schedule_to_disk(path, rec)
        self._current_schedule_name = name
        self.var_sched_label.set(f"Loaded: {name}")
        messagebox.showinfo("Saved", f"Schedule '{name}' saved.")

    # ── Clear week ───────────────────────────────────────────
    def _clear_week(self):
        if not messagebox.askyesno("Clear Week", "Remove all shifts for this week?"):
            return
        self.shifts.clear()
        self._render()

    # ── CSV Export ────────────────────────────────────────────
    def _export_csv(self):
        if not self.shifts:
            messagebox.showinfo("Empty", "No shifts to export.")
            return
        mon = week_monday(self.week_offset)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"shifts_{mon.strftime('%Y-%m-%d')}.csv",
            filetypes=[("CSV", "*.csv")],
            title="Export Shifts",
        )
        if not path:
            return
        rows = []
        for shift in sorted(self.shifts.values(), key=lambda s: (s.day_idx, s.emp_id)):
            emp = self._get_emp(shift.emp_id)
            if not emp:
                continue
            hrs = shift_hours(shift.start, shift.end)
            cost = shift_cost(emp.wage, shift.start, shift.end)
            rows.append(
                {
                    "Day": DAYS[shift.day_idx],
                    "Employee": emp.name,
                    "Role": emp.role,
                    "Wage ($/hr)": f"{emp.wage:.2f}",
                    "Max Hours": f"{emp.max_hours:.2f}",
                    "Available Day": "No" if shift.day_idx in emp.unavailable_days else "Yes",
                    "Start": shift.start,
                    "End": shift.end,
                    "Hours": f"{hrs:.2f}",
                    "Labor Cost": f"{cost:.2f}",
                }
            )
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
            total = sum(float(r["Labor Cost"]) for r in rows)
            f.write(f"\n,,,,,,,,TOTAL,{total:.2f}\n")
        messagebox.showinfo("Exported", f"Exported to:\n{path}")


if __name__ == "__main__":
    app = ShiftPlannerApp()
    app.mainloop()
