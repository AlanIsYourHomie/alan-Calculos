from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Iterable


# ----------------------------- Cálculos ------------------------------------ #

def commercial_mm(inches: int) -> int:
    """
    Conversión métrica nominal usada para mostrar dimensiones:

    1 pulgada ≈ 25 mm

    Ejemplos:
    12" -> 300 mm
    14" -> 350 mm
    16" -> 400 mm
    """
    return inches * 25

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
    def approximate_mm(self) -> tuple[int, int]:
        width_mm = self.width_in * 25
        height_raw_mm = self.height_in * 25

        if self.height_in <= 10:
            height_mm = (
                math.floor(height_raw_mm / 50) + 1
            ) * 50
        else:
            height_mm = height_raw_mm

        return width_mm, height_mm

    @property
    def exact_cm(self) -> tuple[float, float]:
        return self.width_in * 2.54, self.height_in * 2.54


def parse_positive_number(value: str) -> float:
    number = float(value.strip().replace(",", "."))
    if not math.isfinite(number) or number <= 0:
        raise ValueError("El valor debe ser mayor que cero.")
    return number


def required_area_in2(flow_cfm: float, design_velocity_fpm: float) -> float:
    """
    Área mínima necesaria para no superar la velocidad indicada.

    Q = V × A
    A(ft²) = Q(CFM) / V(FPM)
    A(in²) = A(ft²) × 144
    """
    return (flow_cfm / design_velocity_fpm) * 144.0


def generate_duct_options(
    flow_cfm: float,
    design_velocity_fpm: float,
    row_limit: int = 5000,
) -> tuple[list[DuctOption], bool]:
    """
    Genera ductos enteros en pulgadas con estas reglas:

    - ancho > alto;
    - el ancho solo usa números pares: 2, 4, 6, 8, ...;
    - el ancho aumenta de 2 en 2;
    - el alto puede ser cualquier pulgada entera;
    - el alto llega hasta un mínimo de 1 pulgada;
    - la velocidad real no supera la velocidad de diseño.

    Para cada ancho par:
        alto = ceil(área requerida / ancho)
    """
    target_area = required_area_in2(
        flow_cfm,
        design_velocity_fpm,
    )

    # El último ancho necesario corresponde al ducto con alto de 1 pulgada.
    last_width = max(2, math.ceil(target_area))

    # Convierte el límite superior al siguiente número par.
    if last_width % 2 != 0:
        last_width += 1

    options: list[DuctOption] = []
    truncated = False

    # El tercer argumento, 2, hace que el ancho sea siempre par.
    for width in range(2, last_width + 1, 2):
        height = max(
            1,
            math.ceil((target_area / width) - 1e-12),
        )

        # Solo mostrar cuando el ancho sea mayor que el alto.
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


def choose_recommended(
    options: Iterable[DuctOption],
) -> DuctOption:
    """
    Recomienda la primera dimensión viable.

    La lista ya está ordenada por ancho ascendente:
    2, 4, 6, 8, 10, 12, 14...

    Por eso la primera opción es el ducto de menor ancho que cumple:
    - ancho par;
    - ancho mayor que alto;
    - velocidad real igual o menor que la velocidad de diseño.
    """
    values = list(options)

    if not values:
        raise ValueError(
            "No se encontraron dimensiones viables."
        )

    return values[0]

# ----------------------------- Interfaz ------------------------------------ #

class HVACHub(tk.Tk):
    BG = "#F3F6FA"
    SIDEBAR = "#142033"
    SIDEBAR_HOVER = "#20324D"
    ACCENT = "#1976D2"
    ACCENT_DARK = "#125AA3"
    CARD = "#FFFFFF"
    TEXT = "#172033"
    MUTED = "#64748B"
    BORDER = "#DCE3EC"
    SUCCESS = "#137A4A"
    WARNING = "#A05A00"

    def __init__(self) -> None:
        super().__init__()
        self.title("HVAC HUB — Prototipo")
        self.geometry("1180x735")
        self.minsize(1000, 650)
        self.configure(bg=self.BG)

        self._recalc_job: str | None = None
        self._recommended_iid: str | None = None

        self.flow_var = tk.StringVar(value="124")
        self.duct_type_var = tk.StringVar(value="Ramal — 1000 FPM")
        self.velocity_var = tk.StringVar(value="1000")
        self.status_var = tk.StringVar(value="")
        self.area_var = tk.StringVar(value="—")
        self.recommended_var = tk.StringVar(value="—")
        self.recommended_metric_var = tk.StringVar(value="—")
        self.actual_velocity_var = tk.StringVar(value="—")
        self.option_count_var = tk.StringVar(value="—")

        self._configure_styles()
        self._build_layout()
        self._bind_automatic_calculation()
        self._calculate()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Duct.Treeview",
            background=self.CARD,
            fieldbackground=self.CARD,
            foreground=self.TEXT,
            rowheight=31,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Duct.Treeview.Heading",
            background="#E8EEF6",
            foreground=self.TEXT,
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padding=(8, 9),
        )
        style.map(
            "Duct.Treeview",
            background=[("selected", "#CCE4FF")],
            foreground=[("selected", self.TEXT)],
        )
        style.map(
            "Duct.Treeview.Heading",
            background=[("active", "#DDE7F2")],
        )
        style.configure(
            "Hub.TCombobox",
            padding=7,
            fieldbackground=self.CARD,
            background=self.CARD,
        )

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=self.SIDEBAR, width=220)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        tk.Label(
            sidebar,
            text="HVAC",
            bg=self.SIDEBAR,
            fg="white",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(25, 0))

        tk.Label(
            sidebar,
            text="HUB",
            bg=self.SIDEBAR,
            fg="#74B9FF",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=25, pady=(0, 28))

        self._sidebar_button(sidebar, "⌂   Inicio", row=2, enabled=False)
        self._sidebar_button(sidebar, "▰   Ductos", row=3, active=True)
        self._sidebar_button(sidebar, "▦   Rejillas", row=4, enabled=False)
        self._sidebar_button(sidebar, "◈   Difusores", row=5, enabled=False)
        self._sidebar_button(sidebar, "⚙   Configuración", row=6, enabled=False)

        tk.Label(
            sidebar,
            text="Los demás módulos\nse agregarán después.",
            justify="left",
            bg=self.SIDEBAR,
            fg="#92A4BC",
            font=("Segoe UI", 9),
        ).grid(row=9, column=0, sticky="sw", padx=24, pady=24)

    def _sidebar_button(
        self,
        parent: tk.Widget,
        text: str,
        row: int,
        active: bool = False,
        enabled: bool = True,
    ) -> None:
        background = self.ACCENT if active else self.SIDEBAR
        foreground = "white" if enabled or active else "#718198"

        button = tk.Button(
            parent,
            text=text,
            anchor="w",
            padx=23,
            pady=12,
            relief="flat",
            bd=0,
            cursor="hand2" if enabled else "arrow",
            bg=background,
            fg=foreground,
            activebackground=self.ACCENT_DARK if active else self.SIDEBAR_HOVER,
            activeforeground="white",
            disabledforeground="#718198",
            font=("Segoe UI Semibold", 10),
            state="normal" if enabled else "disabled",
        )
        button.grid(row=row, column=0, sticky="ew", padx=10, pady=2)

    def _build_content(self) -> None:
        content = tk.Frame(self, bg=self.BG)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(4, weight=1)

        header = tk.Frame(content, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Calculadora de ductos",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Las dimensiones cambian automáticamente al editar el caudal o la velocidad.",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self._build_input_card(content)
        self._build_summary_cards(content)
        self._build_table(content)

        tk.Label(
            content,
            textvariable=self.status_var,
            bg=self.BG,
            fg=self.WARNING,
            anchor="w",
            font=("Segoe UI", 9),
        ).grid(row=5, column=0, sticky="ew", padx=30, pady=(4, 14))

    def _card(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.CARD,
            highlightbackground=self.BORDER,
            highlightthickness=1,
            bd=0,
        )

    def _build_input_card(self, parent: tk.Widget) -> None:
        card = self._card(parent)
        card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 14))
        card.grid_columnconfigure(5, weight=1)

        tk.Label(
            card,
            text="Datos de diseño",
            bg=self.CARD,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 12),
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=18, pady=(15, 10))

        tk.Label(
            card, text="Caudal", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 9)
        ).grid(row=1, column=0, sticky="w", padx=(18, 6))

        flow_entry = tk.Entry(
            card,
            textvariable=self.flow_var,
            width=13,
            font=("Segoe UI", 12),
            bg="#FBFCFE",
            fg=self.TEXT,
            relief="solid",
            bd=1,
            highlightthickness=0,
        )
        flow_entry.grid(row=2, column=0, sticky="w", padx=(18, 6), pady=(3, 16), ipady=7)

        tk.Label(
            card, text="CFM", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI Semibold", 9)
        ).grid(row=2, column=1, sticky="w", padx=(0, 24))

        tk.Label(
            card, text="Tipo", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 9)
        ).grid(row=1, column=2, sticky="w", padx=(0, 6))

        duct_type = ttk.Combobox(
            card,
            textvariable=self.duct_type_var,
            values=(
                "Ramal — 1000 FPM",
                "Troncal — 1400 FPM",
                "Personalizada",
            ),
            state="readonly",
            width=24,
            style="Hub.TCombobox",
            font=("Segoe UI", 10),
        )
        duct_type.grid(row=2, column=2, sticky="w", padx=(0, 24), pady=(3, 16))
        duct_type.bind("<<ComboboxSelected>>", self._on_type_changed)

        tk.Label(
            card, text="Velocidad de diseño", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 9)
        ).grid(row=1, column=3, sticky="w", padx=(0, 6))

        self.velocity_entry = tk.Entry(
            card,
            textvariable=self.velocity_var,
            width=13,
            font=("Segoe UI", 12),
            bg="#EDF2F7",
            fg=self.TEXT,
            disabledbackground="#EDF2F7",
            disabledforeground=self.TEXT,
            relief="solid",
            bd=1,
            highlightthickness=0,
        )
        self.velocity_entry.grid(row=2, column=3, sticky="w", padx=(0, 6), pady=(3, 16), ipady=7)

        tk.Label(
            card, text="FPM", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI Semibold", 9)
        ).grid(row=2, column=4, sticky="w", padx=(0, 18))

        self.velocity_entry.configure(state="disabled")

    def _build_summary_cards(self, parent: tk.Widget) -> None:
        wrapper = tk.Frame(parent, bg=self.BG)
        wrapper.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 14))
        for column in range(4):
            wrapper.grid_columnconfigure(column, weight=1, uniform="summary")

        self._summary_card(
            wrapper, 0, "ÁREA MÍNIMA", self.area_var, "Según Q ÷ V"
        )
        self._summary_card(
            wrapper, 1, "DUCTO RECOMENDADO", self.recommended_var,
            "", secondary_var=self.recommended_metric_var
        )
        self._summary_card(
            wrapper, 2, "VELOCIDAD REAL", self.actual_velocity_var,
            "No supera el diseño"
        )
        self._summary_card(
            wrapper, 3, "OPCIONES", self.option_count_var,
            "Ancho > alto"
        )

    def _summary_card(
        self,
        parent: tk.Widget,
        column: int,
        title: str,
        value_var: tk.StringVar,
        subtitle: str,
        secondary_var: tk.StringVar | None = None,
    ) -> None:
        card = self._card(parent)
        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 6, 0 if column == 3 else 6),
        )

        tk.Label(
            card,
            text=title,
            bg=self.CARD,
            fg=self.MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(anchor="w", padx=15, pady=(13, 4))

        tk.Label(
            card,
            textvariable=value_var,
            bg=self.CARD,
            fg=self.TEXT if column != 1 else self.ACCENT_DARK,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=15)

        if secondary_var is not None:
            tk.Label(
                card,
                textvariable=secondary_var,
                bg=self.CARD,
                fg=self.MUTED,
                font=("Segoe UI", 8),
            ).pack(anchor="w", padx=15, pady=(2, 13))
        else:
            tk.Label(
                card,
                text=subtitle,
                bg=self.CARD,
                fg=self.MUTED,
                font=("Segoe UI", 8),
            ).pack(anchor="w", padx=15, pady=(2, 13))

    def _build_table(self, parent: tk.Widget) -> None:
        card = self._card(parent)
        card.grid(row=4, column=0, sticky="nsew", padx=28)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        table_header = tk.Frame(card, bg=self.CARD)
        table_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 9))
        table_header.grid_columnconfigure(0, weight=1)

        tk.Label(
            table_header,
            text="Dimensiones viables",
            bg=self.CARD,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 12),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            table_header,
            text='Aprox.: 1" = 25 mm  •  Exacto: 1" = 2.54 cm',
            bg=self.CARD,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=1, sticky="e")

        table_frame = tk.Frame(card, bg=self.CARD)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = (
            "duct",
            "approx_mm",
            "exact_cm",
            "area",
            "velocity",
            "difference",
            "ratio",
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Duct.Treeview",
            selectmode="browse",
        )
        headings = {
            "duct": "Ducto (pulg)",
            "approx_mm": "Aprox. (mm)",
            "exact_cm": "Exacto (cm)",
            "area": "Área (pulg²)",
            "velocity": "Velocidad (FPM)",
            "difference": "Margen",
            "ratio": "Relación",
        }
        widths = {
            "duct": 125,
            "approx_mm": 135,
            "exact_cm": 145,
            "area": 105,
            "velocity": 125,
            "difference": 95,
            "ratio": 80,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                minwidth=70,
                anchor="center",
                stretch=True,
            )

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure(
            "recommended",
            background="#DFF4E9",
            foreground="#0D5E39",
            font=("Segoe UI Semibold", 10),
        )
        self.tree.tag_configure("even", background="#F8FAFC")

    def _bind_automatic_calculation(self) -> None:
        self.flow_var.trace_add("write", self._schedule_calculation)
        self.velocity_var.trace_add("write", self._schedule_calculation)

    def _schedule_calculation(self, *_args: object) -> None:
        if self._recalc_job is not None:
            self.after_cancel(self._recalc_job)
        self._recalc_job = self.after(160, self._calculate)

    def _on_type_changed(self, _event: tk.Event | None = None) -> None:
        selection = self.duct_type_var.get()

        if selection.startswith("Ramal"):
            self.velocity_entry.configure(state="normal")
            self.velocity_var.set("1000")
            self.velocity_entry.configure(state="disabled")
        elif selection.startswith("Troncal"):
            self.velocity_entry.configure(state="normal")
            self.velocity_var.set("1400")
            self.velocity_entry.configure(state="disabled")
        else:
            self.velocity_entry.configure(state="normal")
            self.velocity_entry.focus_set()

        self._schedule_calculation()

    def _clear_results(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.area_var.set("—")
        self.recommended_var.set("—")
        self.recommended_metric_var.set("—")
        self.actual_velocity_var.set("—")
        self.option_count_var.set("—")

    def _calculate(self) -> None:
        self._recalc_job = None

        try:
            flow = parse_positive_number(self.flow_var.get())
            velocity = parse_positive_number(self.velocity_var.get())
            area = required_area_in2(flow, velocity)
            options, truncated = generate_duct_options(flow, velocity)

            if not options:
                raise ValueError(
                    "No hay un ducto rectangular entero con ancho mayor que alto."
                )

            recommended = choose_recommended(options)

        except (ValueError, OverflowError):
            self._clear_results()
            self.status_var.set(
                "Escribe valores numéricos positivos para ver los resultados."
            )
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.area_var.set(f"{area:.2f} pulg²")
        self.recommended_var.set(
            f'{recommended.width_in} × {recommended.height_in} pulg'
        )

        approx_w, approx_h = recommended.approximate_mm
        exact_w, exact_h = recommended.exact_cm
        self.recommended_metric_var.set(
            f"Comercial: {approx_w} × {approx_h} mm  |  "
            f"Exacto: {exact_w:.1f} × {exact_h:.1f} cm"
        )
        self.actual_velocity_var.set(f"{recommended.velocity_fpm:,.0f} FPM")
        self.option_count_var.set(f"{len(options):,}")

        recommended_iid: str | None = None

        for index, option in enumerate(options):
            approx_w, approx_h = option.approximate_mm
            exact_w, exact_h = option.exact_cm
            margin_percent = (
                (velocity - option.velocity_fpm) / velocity
            ) * 100.0

            tags: list[str] = []
            if option == recommended:
                tags.append("recommended")
            elif index % 2:
                tags.append("even")

            iid = self.tree.insert(
                "",
                "end",
                values=(
                    f'{option.width_in} × {option.height_in}',
                    f"{approx_w} × {approx_h}",
                    f"{exact_w:.1f} × {exact_h:.1f}",
                    f"{option.area_in2:,}",
                    f"{option.velocity_fpm:,.0f}",
                    f"{margin_percent:.1f} %",
                    f"{option.aspect_ratio:.2f}:1",
                ),
                tags=tuple(tags),
            )

            if option == recommended:
                recommended_iid = iid

        if recommended_iid is not None:
            self.tree.selection_set(recommended_iid)
            self.tree.focus(recommended_iid)
            self.tree.see(recommended_iid)

        if truncated:
            self.status_var.set(
                "Se muestran las primeras 5,000 opciones para mantener fluida "
                "la interfaz. El cálculo recomendado sí se basa en este rango."
            )
        else:
            self.status_var.set(
                "La fila verde es la primera medida viable con ancho par, "
                "ancho mayor que alto y velocidad inferior al límite."
            )


def main() -> None:
    app = HVACHub()
    app.mainloop()


if __name__ == "__main__":
    main()
