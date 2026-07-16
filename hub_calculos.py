"""
HVAC HUB - Prototipo 3
Módulos:
- Ductos
- Rejillas
- Difusores

El programa recalcula automáticamente al cambiar el caudal o la velocidad.
No requiere paquetes externos: usa solamente tkinter de Python.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Iterable


# =============================================================================
# DATOS Y CÁLCULOS
# =============================================================================

VELOCIDADES_REJILLA = (300, 400, 500, 600, 700, 800, 900, 1000)
PRESION_REJILLA_IN_WG = {
    300: 0.014,
    400: 0.023,
    500: 0.038,
    600: 0.060,
    700: 0.083,
    800: 0.115,
    900: 0.147,
    1000: 0.188,
}

VELOCIDADES_DIFUSOR = (100, 200, 300, 400, 500, 600, 700, 800, 900)


@dataclass(frozen=True)
class DuctOption:
    width_in: int
    height_in: int
    area_in2: int
    velocity_fpm: float
    excess_area_in2: float

    @property
    def aspect_ratio(self) -> float:
        return self.width_in / self.height_in

    @property
    def nominal_mm(self) -> tuple[int, int]:
        """
        Conversión nominal acordada para ductos.

        Ancho:
            pulgadas × 25 mm.

        Alto/largo:
            - por encima de 10": pulgadas × 25 mm;
            - de 10" hacia abajo: pasa al siguiente módulo de 50 mm.

        Ejemplos:
            14 × 12 -> 350 × 300 mm
            16 × 10 -> 400 × 300 mm
            18 × 9  -> 450 × 250 mm
            20 × 8  -> 500 × 250 mm
        """
        width_mm = self.width_in * 25
        raw_height_mm = self.height_in * 25

        if self.height_in <= 10:
            height_mm = (math.floor(raw_height_mm / 50) + 1) * 50
        else:
            height_mm = raw_height_mm

        return width_mm, height_mm

    @property
    def exact_cm(self) -> tuple[float, float]:
        return self.width_in * 2.54, self.height_in * 2.54


@dataclass(frozen=True)
class GrilleSize:
    width_in: int
    height_in: int
    effective_area_ft2: float

    @property
    def label(self) -> str:
        return f"{self.width_in} × {self.height_in}"

    @property
    def nominal_mm(self) -> tuple[int, int]:
        return self.width_in * 25, self.height_in * 25


@dataclass(frozen=True)
class GrilleOption:
    size: GrilleSize
    selected_velocity_fpm: int
    table_capacity_cfm: float
    actual_velocity_fpm: float
    spare_capacity_cfm: float


@dataclass(frozen=True)
class DiffuserPoint:
    capacity_cfm: int
    nc: int | None
    throw_ft: int


@dataclass(frozen=True)
class DiffuserSize:
    width_in: int
    height_in: int
    effective_area_ft2: float
    values: dict[int, DiffuserPoint]

    @property
    def label(self) -> str:
        return f"{self.width_in} × {self.height_in}"

    @property
    def nominal_mm(self) -> tuple[int, int]:
        return self.width_in * 25, self.height_in * 25


@dataclass(frozen=True)
class DiffuserOption:
    size: DiffuserSize
    velocity_fpm: int
    point: DiffuserPoint
    spare_capacity_cfm: float


# Datos de la segunda tabla proporcionada por el usuario.
# La capacidad de la rejilla se calcula como área efectiva × velocidad.
GRILLE_SIZES: tuple[GrilleSize, ...] = (
    GrilleSize(10, 6, 0.291),
    GrilleSize(12, 6, 0.356),
    GrilleSize(10, 8, 0.398),
    GrilleSize(12, 8, 0.485),
    GrilleSize(14, 8, 0.574),
    GrilleSize(12, 12, 0.750),
    GrilleSize(20, 10, 1.040),
    GrilleSize(18, 12, 1.130),
    GrilleSize(30, 8, 1.260),
    GrilleSize(24, 12, 1.550),
    GrilleSize(18, 18, 1.730),
    GrilleSize(24, 14, 1.810),
    GrilleSize(30, 12, 1.960),
    GrilleSize(24, 18, 2.400),
    GrilleSize(30, 18, 3.010),
    GrilleSize(24, 24, 3.200),
    GrilleSize(36, 18, 3.610),
    GrilleSize(30, 24, 4.050),
    GrilleSize(36, 24, 4.830),
    GrilleSize(30, 30, 5.100),
    GrilleSize(36, 30, 6.090),
    GrilleSize(48, 24, 6.500),
    GrilleSize(48, 30, 8.140),
    GrilleSize(48, 36, 9.840),
)


def _diffuser_values(
    capacities: list[int],
    noise_levels: list[int | None],
    throws: list[int],
) -> dict[int, DiffuserPoint]:
    return {
        velocity: DiffuserPoint(capacity, nc, throw)
        for velocity, capacity, nc, throw in zip(
            VELOCIDADES_DIFUSOR,
            capacities,
            noise_levels,
            throws,
        )
    }


# Datos de la primera tabla proporcionada por el usuario.
# Se excluyen 9×9, 15×15 y 21×21 porque se solicitó no usar números impares.
DIFFUSER_SIZES: tuple[DiffuserSize, ...] = (
    DiffuserSize(
        6, 6, 0.21,
        _diffuser_values(
            [20, 40, 75, 120, 140, 170, 200, 225, 250],
            [None, None, None, None, 22, 29, 35, 40, 42],
            [4, 5, 9, 9, 10, 11, 12, 13, 13],
        ),
    ),
    DiffuserSize(
        8, 8, 0.38,
        _diffuser_values(
            [35, 70, 145, 220, 250, 300, 345, 375, 415],
            [None, None, None, None, 24, 31, 36, 40, 43],
            [6, 7, 11, 15, 18, 19, 20, 22, 25],
        ),
    ),
    DiffuserSize(
        10, 10, 0.59,
        _diffuser_values(
            [60, 125, 215, 330, 365, 420, 490, 540, 600],
            [None, None, None, 25, 28, 33, 33, 42, 44],
            [6, 10, 16, 21, 24, 27, 28, 29, 30],
        ),
    ),
    DiffuserSize(
        12, 12, 0.86,
        _diffuser_values(
            [150, 200, 300, 450, 490, 575, 670, 750, 865],
            [None, None, None, 29, 30, 34, 41, 43, 45],
            [10, 14, 20, 26, 30, 31, 32, 33, 34],
        ),
    ),
    DiffuserSize(
        14, 14, 1.16,
        _diffuser_values(
            [170, 250, 390, 580, 680, 810, 925, 1055, 1200],
            [None, None, 22, 30, 31, 35, 42, 43, 46],
            [12, 15, 21, 27, 32, 33, 33, 34, 35],
        ),
    ),
    DiffuserSize(
        16, 16, 1.52,
        _diffuser_values(
            [200, 350, 500, 735, 900, 1075, 1225, 1415, 1600],
            [None, None, 21, 32, 34, 36, 43, 44, 48],
            [13, 17, 22, 28, 34, 35, 37, 39, 44],
        ),
    ),
    DiffuserSize(
        18, 18, 1.92,
        _diffuser_values(
            [250, 450, 620, 900, 1125, 1375, 1600, 1800, 2100],
            [None, None, 22, 33, 35, 37, 44, 45, 48],
            [13, 16, 21, 27, 35, 36, 40, 46, 55],
        ),
    ),
    DiffuserSize(
        20, 20, 2.38,
        _diffuser_values(
            [280, 550, 740, 1060, 1300, 1640, 1925, 2180, 2565],
            [None, None, 22, 33, 34, 37, 45, 46, 49],
            [12, 15, 18, 25, 32, 36, 42, 47, 57],
        ),
    ),
    DiffuserSize(
        22, 22, 2.88,
        _diffuser_values(
            [320, 650, 860, 1225, 1460, 1875, 2315, 2675, 2935],
            [None, 21, 24, 35, 36, 38, 44, 47, 50],
            [11, 14, 18, 24, 30, 34, 42, 47, 56],
        ),
    ),
    DiffuserSize(
        24, 24, 3.42,
        _diffuser_values(
            [380, 750, 990, 1400, 1640, 2060, 2625, 2875, 3160],
            [None, None, 25, 36, 37, 39, 46, 47, 50],
            [9, 14, 17, 26, 30, 37, 45, 49, 55],
        ),
    ),
)


def parse_positive_number(value: str) -> float:
    number = float(value.strip().replace(",", "."))
    if not math.isfinite(number) or number <= 0:
        raise ValueError("El valor debe ser mayor que cero.")
    return number


def required_area_in2(flow_cfm: float, design_velocity_fpm: float) -> float:
    return (flow_cfm / design_velocity_fpm) * 144.0


def generate_duct_options(
    flow_cfm: float,
    design_velocity_fpm: float,
    row_limit: int = 5000,
) -> tuple[list[DuctOption], bool]:
    """
    Genera dimensiones con ancho par y ancho mayor que alto.

    Para cada ancho par calcula el menor alto entero que mantiene la velocidad
    real igual o por debajo de la velocidad de diseño.
    """
    target_area = required_area_in2(flow_cfm, design_velocity_fpm)
    last_width = max(2, math.ceil(target_area))

    if last_width % 2:
        last_width += 1

    options: list[DuctOption] = []
    truncated = False

    for width in range(2, last_width + 1, 2):
        height = max(1, math.ceil((target_area / width) - 1e-12))

        if width <= height:
            continue

        area = width * height
        actual_velocity = flow_cfm / (area / 144.0)
        options.append(
            DuctOption(
                width_in=width,
                height_in=height,
                area_in2=area,
                velocity_fpm=actual_velocity,
                excess_area_in2=area - target_area,
            )
        )

        if len(options) >= row_limit:
            truncated = width < last_width
            break

    return options, truncated


def choose_duct(options: Iterable[DuctOption]) -> DuctOption:
    values = list(options)
    if not values:
        raise ValueError("No se encontraron dimensiones viables.")
    return values[0]


def generate_grille_options(
    flow_cfm: float,
    selected_velocity_fpm: int,
) -> list[GrilleOption]:
    options: list[GrilleOption] = []

    for size in GRILLE_SIZES:
        capacity = size.effective_area_ft2 * selected_velocity_fpm
        if capacity + 1e-9 < flow_cfm:
            continue

        actual_velocity = flow_cfm / size.effective_area_ft2
        options.append(
            GrilleOption(
                size=size,
                selected_velocity_fpm=selected_velocity_fpm,
                table_capacity_cfm=capacity,
                actual_velocity_fpm=actual_velocity,
                spare_capacity_cfm=capacity - flow_cfm,
            )
        )

    return sorted(
        options,
        key=lambda item: (
            item.size.effective_area_ft2,
            item.size.width_in * item.size.height_in,
        ),
    )


def choose_grille(options: Iterable[GrilleOption]) -> GrilleOption:
    values = list(options)
    if not values:
        raise ValueError("El caudal supera la mayor rejilla disponible.")
    return values[0]


def generate_diffuser_options(
    flow_cfm: float,
    selected_velocity_fpm: int,
) -> list[DiffuserOption]:
    options: list[DiffuserOption] = []

    for size in DIFFUSER_SIZES:
        point = size.values[selected_velocity_fpm]
        if point.capacity_cfm < flow_cfm:
            continue

        options.append(
            DiffuserOption(
                size=size,
                velocity_fpm=selected_velocity_fpm,
                point=point,
                spare_capacity_cfm=point.capacity_cfm - flow_cfm,
            )
        )

    return sorted(
        options,
        key=lambda item: (
            item.size.width_in,
            item.point.capacity_cfm,
        ),
    )


def choose_diffuser(options: Iterable[DiffuserOption]) -> DiffuserOption:
    values = list(options)
    if not values:
        raise ValueError("El caudal supera el mayor difusor disponible.")
    return values[0]


# =============================================================================
# INTERFAZ
# =============================================================================

class Palette:
    BG = "#F3F6FA"
    SIDEBAR = "#142033"
    SIDEBAR_HOVER = "#20324D"
    ACCENT = "#1976D2"
    ACCENT_DARK = "#125AA3"
    CARD = "#FFFFFF"
    TEXT = "#172033"
    MUTED = "#64748B"
    BORDER = "#DCE3EC"
    SUCCESS_BG = "#DFF4E9"
    SUCCESS_TEXT = "#0D5E39"
    WARNING = "#A05A00"
    ERROR = "#A72A2A"


class AutoModule(tk.Frame):
    """Base para módulos con cálculo automático mediante StringVar.trace_add."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=Palette.BG)
        self._job: str | None = None

    def schedule(self, *_args: object) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(120, self.calculate)

    def calculate(self) -> None:
        raise NotImplementedError

    @staticmethod
    def card(parent: tk.Widget) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=Palette.CARD,
            highlightbackground=Palette.BORDER,
            highlightthickness=1,
            bd=0,
        )

    @staticmethod
    def label(
        parent: tk.Widget,
        text: str,
        *,
        size: int = 9,
        bold: bool = False,
        color: str | None = None,
    ) -> tk.Label:
        font_name = "Segoe UI Semibold" if bold else "Segoe UI"
        return tk.Label(
            parent,
            text=text,
            bg=parent.cget("bg"),
            fg=color or Palette.TEXT,
            font=(font_name, size),
        )

    @staticmethod
    def clear_tree(tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)


class DuctModule(AutoModule):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.flow_var = tk.StringVar(value="1500")
        self.type_var = tk.StringVar(value="Troncal — 1400 FPM")
        self.velocity_var = tk.StringVar(value="1400")

        self.area_var = tk.StringVar(value="—")
        self.recommended_var = tk.StringVar(value="—")
        self.metric_var = tk.StringVar(value="—")
        self.real_velocity_var = tk.StringVar(value="—")
        self.count_var = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="")

        self._build()
        self.flow_var.trace_add("write", self.schedule)
        self.velocity_var.trace_add("write", self.schedule)
        self.calculate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._header(
            "Calculadora de ductos",
            "Dimensiones rectangulares automáticas con ancho par.",
        )
        self._inputs()
        self._summary()
        self._table()

        tk.Label(
            self,
            textvariable=self.status_var,
            bg=Palette.BG,
            fg=Palette.WARNING,
            anchor="w",
            font=("Segoe UI", 9),
        ).grid(row=5, column=0, sticky="ew", padx=28, pady=(5, 14))

    def _header(self, title: str, subtitle: str) -> None:
        frame = tk.Frame(self, bg=Palette.BG)
        frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))

        tk.Label(
            frame, text=title, bg=Palette.BG, fg=Palette.TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")
        tk.Label(
            frame, text=subtitle, bg=Palette.BG, fg=Palette.MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(3, 0))

    def _inputs(self) -> None:
        card = self.card(self)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))

        tk.Label(
            card, text="Datos de diseño", bg=Palette.CARD, fg=Palette.TEXT,
            font=("Segoe UI Semibold", 12)
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=18, pady=(15, 10))

        self._field_label(card, "Caudal", 0)
        tk.Entry(
            card, textvariable=self.flow_var, width=14,
            font=("Segoe UI", 12), relief="solid", bd=1
        ).grid(row=2, column=0, padx=(18, 6), pady=(3, 16), ipady=7)
        self._unit(card, "CFM", 1)

        self._field_label(card, "Tipo", 2)
        combo = ttk.Combobox(
            card,
            textvariable=self.type_var,
            values=("Ramal — 1000 FPM", "Troncal — 1400 FPM", "Personalizada"),
            state="readonly",
            width=24,
            style="Hub.TCombobox",
        )
        combo.grid(row=2, column=2, padx=(0, 24), pady=(3, 16))
        combo.bind("<<ComboboxSelected>>", self._type_changed)

        self._field_label(card, "Velocidad de diseño", 3)
        self.velocity_entry = tk.Entry(
            card, textvariable=self.velocity_var, width=14,
            font=("Segoe UI", 12), relief="solid", bd=1,
            disabledbackground="#EDF2F7", disabledforeground=Palette.TEXT,
        )
        self.velocity_entry.grid(row=2, column=3, padx=(0, 6), pady=(3, 16), ipady=7)
        self.velocity_entry.configure(state="disabled")
        self._unit(card, "FPM", 4)

    @staticmethod
    def _field_label(parent: tk.Widget, text: str, column: int) -> None:
        tk.Label(
            parent, text=text, bg=Palette.CARD, fg=Palette.MUTED,
            font=("Segoe UI", 9)
        ).grid(row=1, column=column, sticky="w", padx=(18 if column == 0 else 0, 6))

    @staticmethod
    def _unit(parent: tk.Widget, text: str, column: int) -> None:
        tk.Label(
            parent, text=text, bg=Palette.CARD, fg=Palette.MUTED,
            font=("Segoe UI Semibold", 9)
        ).grid(row=2, column=column, sticky="w", padx=(0, 24))

    def _type_changed(self, _event: tk.Event | None = None) -> None:
        selection = self.type_var.get()
        self.velocity_entry.configure(state="normal")

        if selection.startswith("Ramal"):
            self.velocity_var.set("1000")
            self.velocity_entry.configure(state="disabled")
        elif selection.startswith("Troncal"):
            self.velocity_var.set("1400")
            self.velocity_entry.configure(state="disabled")
        else:
            self.velocity_entry.focus_set()

        self.schedule()

    def _summary(self) -> None:
        wrapper = tk.Frame(self, bg=Palette.BG)
        wrapper.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        for column in range(4):
            wrapper.grid_columnconfigure(column, weight=1, uniform="duct-summary")

        summary_card(wrapper, 0, "ÁREA MÍNIMA", self.area_var, "Según Q ÷ V")
        summary_card(
            wrapper, 1, "DUCTO RECOMENDADO", self.recommended_var,
            secondary_var=self.metric_var, accent=True
        )
        summary_card(
            wrapper, 2, "VELOCIDAD REAL", self.real_velocity_var,
            "No supera el diseño"
        )
        summary_card(wrapper, 3, "OPCIONES", self.count_var, "Ancho > alto")

    def _table(self) -> None:
        card = self.card(self)
        card.grid(row=4, column=0, sticky="nsew", padx=28)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        header = tk.Frame(card, bg=Palette.CARD)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 9))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header, text="Dimensiones viables", bg=Palette.CARD, fg=Palette.TEXT,
            font=("Segoe UI Semibold", 12)
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text='Nominal según regla acordada  •  Exacto: 1" = 2.54 cm',
            bg=Palette.CARD, fg=Palette.MUTED, font=("Segoe UI", 9)
        ).grid(row=0, column=1, sticky="e")

        columns = ("duct", "nominal", "exact", "area", "velocity", "margin", "ratio")
        headings = (
            "Ducto (pulg)", "Nominal (mm)", "Exacto (cm)", "Área (pulg²)",
            "Velocidad (FPM)", "Margen", "Relación"
        )
        widths = (120, 135, 135, 100, 125, 90, 80)

        self.tree = make_tree(card, columns, headings, widths)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 31), pady=(0, 16))
        attach_scrollbar(card, self.tree, row=1)

    def calculate(self) -> None:
        self._job = None
        try:
            flow = parse_positive_number(self.flow_var.get())
            velocity = parse_positive_number(self.velocity_var.get())
            area = required_area_in2(flow, velocity)
            options, truncated = generate_duct_options(flow, velocity)
            recommended = choose_duct(options)
        except (ValueError, OverflowError):
            self.clear_tree(self.tree)
            for variable in (
                self.area_var, self.recommended_var, self.metric_var,
                self.real_velocity_var, self.count_var
            ):
                variable.set("—")
            self.status_var.set("Escribe valores numéricos positivos.")
            return

        self.clear_tree(self.tree)
        self.area_var.set(f"{area:.2f} pulg²")
        self.recommended_var.set(f"{recommended.width_in} × {recommended.height_in} pulg")

        nominal_w, nominal_h = recommended.nominal_mm
        exact_w, exact_h = recommended.exact_cm
        self.metric_var.set(
            f"{nominal_w} × {nominal_h} mm  |  {exact_w:.1f} × {exact_h:.1f} cm"
        )
        self.real_velocity_var.set(f"{recommended.velocity_fpm:,.0f} FPM")
        self.count_var.set(f"{len(options):,}")

        recommended_iid: str | None = None
        for index, option in enumerate(options):
            nominal_w, nominal_h = option.nominal_mm
            exact_w, exact_h = option.exact_cm
            margin = ((velocity - option.velocity_fpm) / velocity) * 100

            tags = ["recommended"] if option == recommended else (["even"] if index % 2 else [])
            iid = self.tree.insert(
                "", "end",
                values=(
                    f"{option.width_in} × {option.height_in}",
                    f"{nominal_w} × {nominal_h}",
                    f"{exact_w:.1f} × {exact_h:.1f}",
                    f"{option.area_in2:,}",
                    f"{option.velocity_fpm:,.0f}",
                    f"{margin:.1f} %",
                    f"{option.aspect_ratio:.2f}:1",
                ),
                tags=tuple(tags),
            )
            if option == recommended:
                recommended_iid = iid

        select_recommended(self.tree, recommended_iid)
        self.status_var.set(
            "La fila verde es la primera medida viable con ancho par."
            + (" La lista fue limitada." if truncated else "")
        )


class GrilleModule(AutoModule):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.flow_var = tk.StringVar(value="500")
        self.velocity_var = tk.StringVar(value="500")

        self.recommended_var = tk.StringVar(value="—")
        self.metric_var = tk.StringVar(value="—")
        self.area_var = tk.StringVar(value="—")
        self.actual_velocity_var = tk.StringVar(value="—")
        self.capacity_var = tk.StringVar(value="—")
        self.pressure_var = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="")

        self._build()
        self.flow_var.trace_add("write", self.schedule)
        self.velocity_var.trace_add("write", self.schedule)
        self.calculate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        module_header(
            self,
            "Calculadora de rejillas",
            "Selección basada en área efectiva y velocidad de cara.",
        )

        card = self.card(self)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))

        tk.Label(
            card, text="Datos de selección", bg=Palette.CARD, fg=Palette.TEXT,
            font=("Segoe UI Semibold", 12)
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=18, pady=(15, 10))

        input_label(card, "Caudal de la rejilla", 0)
        tk.Entry(
            card, textvariable=self.flow_var, width=15,
            font=("Segoe UI", 12), relief="solid", bd=1
        ).grid(row=2, column=0, padx=(18, 6), pady=(3, 16), ipady=7)
        input_unit(card, "CFM", 1)

        input_label(card, "Velocidad de cara", 2)
        combo = ttk.Combobox(
            card,
            textvariable=self.velocity_var,
            values=tuple(str(value) for value in VELOCIDADES_REJILLA),
            state="readonly",
            width=15,
            style="Hub.TCombobox",
        )
        combo.grid(row=2, column=2, padx=(0, 6), pady=(3, 16))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.schedule())
        input_unit(card, "FPM", 3)

        wrapper = tk.Frame(self, bg=Palette.BG)
        wrapper.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        for column in range(5):
            wrapper.grid_columnconfigure(column, weight=1, uniform="grille-summary")

        summary_card(
            wrapper, 0, "REJILLA RECOMENDADA", self.recommended_var,
            secondary_var=self.metric_var, accent=True
        )
        summary_card(wrapper, 1, "ÁREA EFECTIVA", self.area_var, "ft²")
        summary_card(
            wrapper, 2, "VELOCIDAD REAL", self.actual_velocity_var,
            "Con el caudal ingresado"
        )
        summary_card(wrapper, 3, "CAPACIDAD TABLA", self.capacity_var, "CFM")
        summary_card(wrapper, 4, "PRESIÓN NEGATIVA", self.pressure_var, "in H₂O")

        table_card = self.card(self)
        table_card.grid(row=4, column=0, sticky="nsew", padx=28)
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)

        table_title(
            table_card,
            "Rejillas viables",
            "Solo tamaños pares incluidos en la tabla.",
        )

        columns = ("size", "metric", "area", "capacity", "actual", "spare", "margin")
        headings = (
            "Tamaño (pulg)", "Nominal (mm)", "Área efectiva (ft²)",
            "Capacidad (CFM)", "Velocidad real", "Reserva (CFM)", "Margen"
        )
        widths = (115, 125, 125, 120, 115, 115, 90)
        self.tree = make_tree(table_card, columns, headings, widths)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 31), pady=(0, 16))
        attach_scrollbar(table_card, self.tree, row=1)

        tk.Label(
            self, textvariable=self.status_var, bg=Palette.BG,
            fg=Palette.WARNING, anchor="w", font=("Segoe UI", 9)
        ).grid(row=5, column=0, sticky="ew", padx=28, pady=(5, 14))

    def calculate(self) -> None:
        self._job = None
        try:
            flow = parse_positive_number(self.flow_var.get())
            velocity = int(self.velocity_var.get())
            options = generate_grille_options(flow, velocity)
            recommended = choose_grille(options)
        except (ValueError, KeyError):
            self.clear_tree(self.tree)
            for variable in (
                self.recommended_var, self.metric_var, self.area_var,
                self.actual_velocity_var, self.capacity_var, self.pressure_var
            ):
                variable.set("—")
            self.status_var.set(
                "Escribe un caudal válido o selecciona una velocidad de la tabla."
            )
            return

        self.clear_tree(self.tree)

        width_mm, height_mm = recommended.size.nominal_mm
        self.recommended_var.set(f"{recommended.size.label} pulg")
        self.metric_var.set(f"{width_mm} × {height_mm} mm nominal")
        self.area_var.set(f"{recommended.size.effective_area_ft2:.3f}")
        self.actual_velocity_var.set(f"{recommended.actual_velocity_fpm:,.0f} FPM")
        self.capacity_var.set(f"{recommended.table_capacity_cfm:,.0f}")
        self.pressure_var.set(f"{PRESION_REJILLA_IN_WG[velocity]:.3f}")

        recommended_iid: str | None = None
        for index, option in enumerate(options):
            width_mm, height_mm = option.size.nominal_mm
            margin = option.spare_capacity_cfm / flow * 100
            tags = ["recommended"] if option == recommended else (["even"] if index % 2 else [])

            iid = self.tree.insert(
                "", "end",
                values=(
                    option.size.label,
                    f"{width_mm} × {height_mm}",
                    f"{option.size.effective_area_ft2:.3f}",
                    f"{option.table_capacity_cfm:,.0f}",
                    f"{option.actual_velocity_fpm:,.0f} FPM",
                    f"{option.spare_capacity_cfm:,.0f}",
                    f"{margin:.1f} %",
                ),
                tags=tuple(tags),
            )
            if option == recommended:
                recommended_iid = iid

        select_recommended(self.tree, recommended_iid)
        self.status_var.set(
            "La fila verde es la menor área efectiva que admite el caudal "
            "sin superar la velocidad seleccionada."
        )


class DiffuserModule(AutoModule):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)

        self.flow_var = tk.StringVar(value="500")
        self.velocity_var = tk.StringVar(value="500")

        self.recommended_var = tk.StringVar(value="—")
        self.metric_var = tk.StringVar(value="—")
        self.capacity_var = tk.StringVar(value="—")
        self.nc_var = tk.StringVar(value="—")
        self.throw_var = tk.StringVar(value="—")
        self.per_side_var = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="")

        self._build()
        self.flow_var.trace_add("write", self.schedule)
        self.velocity_var.trace_add("write", self.schedule)
        self.calculate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        module_header(
            self,
            "Calculadora de difusores",
            "Selección directa según caudal total y velocidad en el cuello.",
        )

        card = self.card(self)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))

        tk.Label(
            card, text="Datos de selección", bg=Palette.CARD, fg=Palette.TEXT,
            font=("Segoe UI Semibold", 12)
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=18, pady=(15, 10))

        input_label(card, "Caudal del difusor", 0)
        tk.Entry(
            card, textvariable=self.flow_var, width=15,
            font=("Segoe UI", 12), relief="solid", bd=1
        ).grid(row=2, column=0, padx=(18, 6), pady=(3, 16), ipady=7)
        input_unit(card, "CFM", 1)

        input_label(card, "Velocidad en cuello", 2)
        combo = ttk.Combobox(
            card,
            textvariable=self.velocity_var,
            values=tuple(str(value) for value in VELOCIDADES_DIFUSOR),
            state="readonly",
            width=15,
            style="Hub.TCombobox",
        )
        combo.grid(row=2, column=2, padx=(0, 6), pady=(3, 16))
        combo.bind("<<ComboboxSelected>>", lambda _event: self.schedule())
        input_unit(card, "FPM", 3)

        wrapper = tk.Frame(self, bg=Palette.BG)
        wrapper.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        for column in range(5):
            wrapper.grid_columnconfigure(column, weight=1, uniform="diff-summary")

        summary_card(
            wrapper, 0, "DIFUSOR RECOMENDADO", self.recommended_var,
            secondary_var=self.metric_var, accent=True
        )
        summary_card(wrapper, 1, "CAPACIDAD TABLA", self.capacity_var, "CFM total")
        summary_card(wrapper, 2, "NC", self.nc_var, "Nivel de ruido")
        summary_card(wrapper, 3, "TIRO", self.throw_var, "pies")
        summary_card(wrapper, 4, "CFM POR LADO", self.per_side_var, "Cuatro vías")

        table_card = self.card(self)
        table_card.grid(row=4, column=0, sticky="nsew", padx=28)
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)

        table_title(
            table_card,
            "Difusores viables",
            "Las medidas impares de la tabla fueron excluidas.",
        )

        columns = ("size", "metric", "capacity", "nc", "per_side", "throw", "spare")
        headings = (
            "Tamaño (pulg)", "Nominal (mm)", "Capacidad (CFM)", "NC",
            "CFM por lado", "Tiro (pies)", "Reserva (CFM)"
        )
        widths = (115, 125, 125, 75, 110, 100, 115)
        self.tree = make_tree(table_card, columns, headings, widths)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 31), pady=(0, 16))
        attach_scrollbar(table_card, self.tree, row=1)

        tk.Label(
            self, textvariable=self.status_var, bg=Palette.BG,
            fg=Palette.WARNING, anchor="w", font=("Segoe UI", 9)
        ).grid(row=5, column=0, sticky="ew", padx=28, pady=(5, 14))

    def calculate(self) -> None:
        self._job = None
        try:
            flow = parse_positive_number(self.flow_var.get())
            velocity = int(self.velocity_var.get())
            options = generate_diffuser_options(flow, velocity)
            recommended = choose_diffuser(options)
        except (ValueError, KeyError):
            self.clear_tree(self.tree)
            for variable in (
                self.recommended_var, self.metric_var, self.capacity_var,
                self.nc_var, self.throw_var, self.per_side_var
            ):
                variable.set("—")
            self.status_var.set(
                "Escribe un caudal válido o selecciona una velocidad de la tabla."
            )
            return

        self.clear_tree(self.tree)

        width_mm, height_mm = recommended.size.nominal_mm
        self.recommended_var.set(f"{recommended.size.label} pulg")
        self.metric_var.set(f"{width_mm} × {height_mm} mm nominal")
        self.capacity_var.set(f"{recommended.point.capacity_cfm:,}")
        self.nc_var.set(
            "—" if recommended.point.nc is None else str(recommended.point.nc)
        )
        self.throw_var.set(f"{recommended.point.throw_ft} pies")
        self.per_side_var.set(f"{recommended.point.capacity_cfm / 4:.0f}")

        recommended_iid: str | None = None
        for index, option in enumerate(options):
            width_mm, height_mm = option.size.nominal_mm
            tags = ["recommended"] if option == recommended else (["even"] if index % 2 else [])

            iid = self.tree.insert(
                "", "end",
                values=(
                    option.size.label,
                    f"{width_mm} × {height_mm}",
                    f"{option.point.capacity_cfm:,}",
                    "—" if option.point.nc is None else option.point.nc,
                    f"{option.point.capacity_cfm / 4:.0f}",
                    option.point.throw_ft,
                    f"{option.spare_capacity_cfm:,.0f}",
                ),
                tags=tuple(tags),
            )
            if option == recommended:
                recommended_iid = iid

        select_recommended(self.tree, recommended_iid)
        self.status_var.set(
            "Base transcrita de la tabla escaneada. Conviene verificar los "
            "valores de NC y tiro antes de usarla como selección final."
        )


def module_header(parent: tk.Widget, title: str, subtitle: str) -> None:
    frame = tk.Frame(parent, bg=Palette.BG)
    frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))

    tk.Label(
        frame, text=title, bg=Palette.BG, fg=Palette.TEXT,
        font=("Segoe UI", 22, "bold")
    ).pack(anchor="w")
    tk.Label(
        frame, text=subtitle, bg=Palette.BG, fg=Palette.MUTED,
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(3, 0))


def input_label(parent: tk.Widget, text: str, column: int) -> None:
    tk.Label(
        parent, text=text, bg=Palette.CARD, fg=Palette.MUTED,
        font=("Segoe UI", 9)
    ).grid(row=1, column=column, sticky="w", padx=(18 if column == 0 else 0, 6))


def input_unit(parent: tk.Widget, text: str, column: int) -> None:
    tk.Label(
        parent, text=text, bg=Palette.CARD, fg=Palette.MUTED,
        font=("Segoe UI Semibold", 9)
    ).grid(row=2, column=column, sticky="w", padx=(0, 24))


def summary_card(
    parent: tk.Widget,
    column: int,
    title: str,
    value_var: tk.StringVar,
    subtitle: str = "",
    *,
    secondary_var: tk.StringVar | None = None,
    accent: bool = False,
) -> None:
    card = tk.Frame(
        parent,
        bg=Palette.CARD,
        highlightbackground=Palette.BORDER,
        highlightthickness=1,
    )
    card.grid(
        row=0,
        column=column,
        sticky="nsew",
        padx=(0 if column == 0 else 5, 0 if column == 4 else 5),
    )

    tk.Label(
        card, text=title, bg=Palette.CARD, fg=Palette.MUTED,
        font=("Segoe UI Semibold", 8)
    ).pack(anchor="w", padx=14, pady=(12, 4))

    tk.Label(
        card, textvariable=value_var, bg=Palette.CARD,
        fg=Palette.ACCENT_DARK if accent else Palette.TEXT,
        font=("Segoe UI", 15, "bold")
    ).pack(anchor="w", padx=14)

    if secondary_var is not None:
        tk.Label(
            card, textvariable=secondary_var, bg=Palette.CARD, fg=Palette.MUTED,
            font=("Segoe UI", 8), wraplength=190, justify="left"
        ).pack(anchor="w", padx=14, pady=(2, 12))
    else:
        tk.Label(
            card, text=subtitle, bg=Palette.CARD, fg=Palette.MUTED,
            font=("Segoe UI", 8)
        ).pack(anchor="w", padx=14, pady=(2, 12))


def table_title(parent: tk.Widget, title: str, subtitle: str) -> None:
    header = tk.Frame(parent, bg=Palette.CARD)
    header.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 9))
    header.grid_columnconfigure(0, weight=1)

    tk.Label(
        header, text=title, bg=Palette.CARD, fg=Palette.TEXT,
        font=("Segoe UI Semibold", 12)
    ).grid(row=0, column=0, sticky="w")
    tk.Label(
        header, text=subtitle, bg=Palette.CARD, fg=Palette.MUTED,
        font=("Segoe UI", 9)
    ).grid(row=0, column=1, sticky="e")


def make_tree(
    parent: tk.Widget,
    columns: tuple[str, ...],
    headings: tuple[str, ...],
    widths: tuple[int, ...],
) -> ttk.Treeview:
    tree = ttk.Treeview(
        parent,
        columns=columns,
        show="headings",
        style="Hub.Treeview",
        selectmode="browse",
    )

    for column, heading, width in zip(columns, headings, widths):
        tree.heading(column, text=heading)
        tree.column(column, width=width, minwidth=65, anchor="center", stretch=True)

    tree.tag_configure(
        "recommended",
        background=Palette.SUCCESS_BG,
        foreground=Palette.SUCCESS_TEXT,
        font=("Segoe UI Semibold", 10),
    )
    tree.tag_configure("even", background="#F8FAFC")
    return tree


def attach_scrollbar(parent: tk.Widget, tree: ttk.Treeview, row: int) -> None:
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=row, column=0, sticky="nse", padx=(0, 16), pady=(0, 16))


def select_recommended(tree: ttk.Treeview, iid: str | None) -> None:
    if iid is None:
        return
    tree.selection_set(iid)
    tree.focus(iid)
    tree.see(iid)


class HVACHub(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("HVAC HUB")
        self.geometry("1260x760")
        self.minsize(1050, 680)
        self.configure(bg=Palette.BG)

        self._buttons: dict[str, tk.Button] = {}
        self._modules: dict[str, tk.Frame] = {}

        self._configure_styles()
        self._build()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Hub.Treeview",
            background=Palette.CARD,
            fieldbackground=Palette.CARD,
            foreground=Palette.TEXT,
            rowheight=31,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Hub.Treeview.Heading",
            background="#E8EEF6",
            foreground=Palette.TEXT,
            relief="flat",
            font=("Segoe UI Semibold", 9),
            padding=(6, 9),
        )
        style.map(
            "Hub.Treeview",
            background=[("selected", "#CCE4FF")],
            foreground=[("selected", Palette.TEXT)],
        )
        style.configure(
            "Hub.TCombobox",
            padding=7,
            fieldbackground=Palette.CARD,
            background=Palette.CARD,
        )

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        content = tk.Frame(self, bg=Palette.BG)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._modules = {
            "ductos": DuctModule(content),
            "rejillas": GrilleModule(content),
            "difusores": DiffuserModule(content),
        }

        for module in self._modules.values():
            module.grid(row=0, column=0, sticky="nsew")

        self.show_module("ductos")

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=Palette.SIDEBAR, width=220)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        tk.Label(
            sidebar, text="HVAC", bg=Palette.SIDEBAR, fg="white",
            font=("Segoe UI", 22, "bold")
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(25, 0))
        tk.Label(
            sidebar, text="HUB", bg=Palette.SIDEBAR, fg="#74B9FF",
            font=("Segoe UI", 13, "bold")
        ).grid(row=1, column=0, sticky="w", padx=25, pady=(0, 28))

        items = (
            ("ductos", "▰   Ductos"),
            ("rejillas", "▦   Rejillas"),
            ("difusores", "◈   Difusores"),
        )

        for row, (key, text) in enumerate(items, start=2):
            button = tk.Button(
                sidebar,
                text=text,
                anchor="w",
                padx=23,
                pady=12,
                relief="flat",
                bd=0,
                cursor="hand2",
                bg=Palette.SIDEBAR,
                fg="white",
                activebackground=Palette.SIDEBAR_HOVER,
                activeforeground="white",
                font=("Segoe UI Semibold", 10),
                command=lambda selected=key: self.show_module(selected),
            )
            button.grid(row=row, column=0, sticky="ew", padx=10, pady=2)
            self._buttons[key] = button

        tk.Label(
            sidebar,
            text="Base inicial de selección.\nLos catálogos pueden editarse\ndespués en el mismo archivo.",
            justify="left",
            bg=Palette.SIDEBAR,
            fg="#92A4BC",
            font=("Segoe UI", 9),
        ).grid(row=9, column=0, sticky="sw", padx=24, pady=24)

    def show_module(self, name: str) -> None:
        self._modules[name].tkraise()

        for key, button in self._buttons.items():
            if key == name:
                button.configure(
                    bg=Palette.ACCENT,
                    activebackground=Palette.ACCENT_DARK,
                )
            else:
                button.configure(
                    bg=Palette.SIDEBAR,
                    activebackground=Palette.SIDEBAR_HOVER,
                )


def main() -> None:
    app = HVACHub()
    app.mainloop()


if __name__ == "__main__":
    main()
