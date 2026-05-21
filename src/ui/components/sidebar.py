from dash import dcc, html


def sidebar_clamp(min_px, preferred_dvh, max_px):
    return f"clamp({min_px}px, {preferred_dvh}dvh, {max_px}px)"


def overlay_clamp(min_px, preferred_vmin, max_px):
    return f"clamp({min_px}px, {preferred_vmin}vmin, {max_px}px)"


def overlay_width_clamp(min_px, preferred_dvw, max_px):
    return f"clamp({min_px}px, {preferred_dvw}dvw, {max_px}px)"


PROGRESS_BAR_HEIGHT = "var(--bottom-bar-height)"


def sidebar_row_count(component):
    if isinstance(component, (list, tuple)):
        return sum(sidebar_row_count(child) for child in component)

    class_name = getattr(component, "className", "") or ""
    if "sidebar-section-title" in class_name or "sidebar-stat" in class_name:
        return 1

    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        return max(1, sum(sidebar_row_count(child) for child in children))

    return 1


def sidebar_content_grid_style(row_count):
    return {
        "display": "grid",
        "gridAutoRows": "minmax(min-content, auto)",
        "gap": sidebar_clamp(5, 0.8, 9),
        "alignItems": "center",
        "alignContent": "start",
        "height": "auto",
        "minHeight": "0",
    }


def sidebar_detail_panel_style(content):
    return {
        "flex": "1 1 auto",
        "minHeight": "0",
        "height": "100%",
        "display": "flex",
        "flexDirection": "column",
        "overflowY": "auto",
        "overflowX": "hidden",
        "padding": sidebar_clamp(10, 1.6, 18),
        "marginTop": "0",
        "borderRadius": sidebar_clamp(8, 1.5, 14),
        "backgroundColor": "rgba(255, 255, 255, 0.11)",
        "border": "1px solid rgba(255, 255, 255, 0.16)",
        "boxShadow": "inset 0 1px 0 rgba(255, 255, 255, 0.08)",
    }


def sidebar_fit_area_style(detail_content, summary_rows):
    return {
        "flex": "1 1 auto",
        "minHeight": "0",
        "overflowY": "hidden",
        "overflowX": "hidden",
        "display": "flex",
        "flexDirection": "column",
        "justifyContent": "flex-start",
        "gap": sidebar_clamp(6, 0.9, 10),
        "paddingBottom": "0",
    }


def button_style(background_color, color="#0f172a"):
    return {
        "width": "100%",
        "padding": f"{sidebar_clamp(4, 0.6, 7)} {sidebar_clamp(8, 1.1, 12)}",
        "border": "none",
        "borderRadius": sidebar_clamp(6, 1.1, 10),
        "backgroundColor": background_color,
        "color": color,
        "cursor": "pointer",
        "fontSize": sidebar_clamp(9, 1.35, 12),
        "fontWeight": "600",
        "lineHeight": "1.12",
        "height": "auto",
        "minHeight": sidebar_clamp(28, 3.6, 36),
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "flex-start",
        "textAlign": "left",
    }


SIDEBAR_BUTTON_STYLE = button_style("rgba(255, 255, 255, 0.08)", "white")
SIDEBAR_CONTROL_ROWS = 4
SIDEBAR_PANEL_SUMMARY = "summary"
SIDEBAR_PANEL_DETAIL = "detail"


def sidebar_panel_container_style(is_active):
    return {
        "display": "flex" if is_active else "none",
        "flex": "1 1 auto",
        "minHeight": "0",
        "height": "100%",
        "width": "100%",
        "flexDirection": "column",
    }


def sidebar_tab_button_style(is_active):
    return {
        "flex": "1 1 0",
        "minWidth": "0",
        "padding": f"{sidebar_clamp(5, 0.75, 8)} {sidebar_clamp(7, 1, 11)}",
        "border": "1px solid rgba(255, 255, 255, 0.22)" if is_active else "1px solid rgba(255, 255, 255, 0.10)",
        "borderRadius": sidebar_clamp(7, 1.15, 10),
        "backgroundColor": "rgba(56, 189, 248, 0.22)" if is_active else "rgba(255, 255, 255, 0.07)",
        "color": "#ffffff",
        "boxShadow": "inset 0 1px 0 rgba(255, 255, 255, 0.10)" if is_active else "none",
        "cursor": "pointer",
        "fontSize": sidebar_clamp(9, 1.35, 12),
        "fontWeight": "800" if is_active else "650",
        "lineHeight": "1.12",
        "letterSpacing": "0",
        "textAlign": "center",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "whiteSpace": "nowrap",
        "transition": "background-color 160ms ease, border-color 160ms ease",
    }


def sidebar_tab_group_style():
    return {
        "flex": "0 0 auto",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "gap": sidebar_clamp(5, 0.8, 8),
        "padding": sidebar_clamp(4, 0.7, 7),
        "borderRadius": sidebar_clamp(8, 1.3, 12),
        "backgroundColor": "rgba(255, 255, 255, 0.05)",
        "border": "1px solid rgba(255, 255, 255, 0.08)",
        "minHeight": "0",
    }


def sidebar_section_title(text):
    return html.P(
        text,
        className="sidebar-section-title",
        style={
            "display": "flex",
            "alignItems": "center",
            "margin": "0",
            "fontSize": sidebar_clamp(10, 1.9, 16),
            "fontWeight": "700",
            "lineHeight": "1.14",
            "letterSpacing": "0",
            "textTransform": "none",
            "color": "#ffffff",
        },
    )


def sidebar_stat(label, value, color="#0f172a"):
    value_color = "#ffffff" if color == "#0f172a" else color
    return html.Div(
        [
            html.Span(
                label,
                style={
                    "color": "#ffffff",
                    "minWidth": "0",
                    "flex": "1 1 auto",
                    "whiteSpace": "normal",
                    "overflowWrap": "break-word",
                },
            ),
            html.Span(
                value,
                style={
                    "fontWeight": "800",
                    "color": value_color,
                    "flex": "0 0 auto",
                    "maxWidth": "48%",
                    "textAlign": "right",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
            ),
        ],
        className="sidebar-stat",
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "gap": sidebar_clamp(8, 1.25, 13),
            "padding": f"{sidebar_clamp(2, 0.45, 5)} 0",
            "fontSize": sidebar_clamp(9, 1.65, 14),
            "lineHeight": "1.18",
            "minHeight": sidebar_clamp(20, 3, 28),
        },
    )


def seed_input(label, input_id, value=0, compact=False):
    label_font_size = sidebar_clamp(7, 1.15, 10) if compact else sidebar_clamp(9, 1.55, 13)
    input_padding = (
        f"{sidebar_clamp(1, 0.18, 2)} {sidebar_clamp(2, 0.35, 4)}"
        if compact
        else f"{sidebar_clamp(3, 0.65, 7)} {sidebar_clamp(5, 0.9, 10)}"
    )
    input_border_radius = sidebar_clamp(4, 0.75, 7) if compact else sidebar_clamp(5, 1, 9)
    input_font_size = sidebar_clamp(8, 1.25, 11) if compact else sidebar_clamp(10, 1.6, 14)
    input_min_height = sidebar_clamp(18, 3, 28) if compact else sidebar_clamp(22, 3.2, 34)
    label_gap = sidebar_clamp(1, 0.2, 3) if compact else sidebar_clamp(2, 0.35, 5)
    return html.Label(
        [
            html.Span(
                label,
                style={
                    "color": "white",
                    "fontSize": label_font_size,
                    "fontWeight": "700",
                    "lineHeight": "1",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "minWidth": "0",
                },
            ),
            dcc.Input(
                id=input_id,
                type="text",
                value=value,
                debounce=True,
                inputMode="numeric",
                className="sidebar-input",
                style={
                    "width": "100%",
                    "minWidth": "0",
                    "padding": input_padding,
                    "borderRadius": input_border_radius,
                    "border": "1px solid rgba(255,255,255,0.2)",
                    "backgroundColor": "rgba(15, 23, 42, 0.9)",
                    "color": "white",
                    "fontSize": input_font_size,
                    "lineHeight": "1.1",
                    "height": "auto",
                    "minHeight": input_min_height,
                    "boxSizing": "border-box",
                },
            ),
        ],
        style={"display": "grid", "gap": label_gap, "minWidth": "0"},
    )


def build_sidebar_controls():
    return html.Div(
        [
            html.Button("Avanzar 1 mes", id="step-btn", n_clicks=0, style=SIDEBAR_BUTTON_STYLE),
            html.Button("Mostrar corrientes", id="toggle-currents-btn", n_clicks=0, style=SIDEBAR_BUTTON_STYLE),
            html.Button("Mostrar transporte previsto", id="toggle-transport-btn", n_clicks=0, style=SIDEBAR_BUTTON_STYLE),
            html.Button("Reiniciar simulación", id="reset-btn", n_clicks=0, style=SIDEBAR_BUTTON_STYLE),
        ],
        className="sidebar-controls",
        style={
            "flex": "0 0 auto",
            "minHeight": "0",
            "display": "grid",
            "gridTemplateRows": f"repeat({SIDEBAR_CONTROL_ROWS}, minmax({sidebar_clamp(28, 3.6, 36)}, auto))",
            "alignItems": "stretch",
            "alignContent": "stretch",
            "gap": sidebar_clamp(3, 0.45, 5),
            "marginBottom": "0",
            "padding": sidebar_clamp(5, 0.75, 8),
            "borderRadius": sidebar_clamp(7, 1.15, 10),
            "backgroundColor": "rgba(255, 255, 255, 0.05)",
            "overflow": "hidden",
        },
    )


def build_save_simulation_button():
    return html.Div(
        html.Button(
            "Guardar simulación",
            id="save-simulation-btn",
            n_clicks=0,
            style={
                **SIDEBAR_BUTTON_STYLE,
                "justifyContent": "center",
                "textAlign": "center",
                "backgroundColor": "rgba(56, 189, 248, 0.16)",
                "border": "1px solid rgba(56, 189, 248, 0.32)",
            },
        ),
        style={
            "flex": "0 0 auto",
            "minHeight": "0",
            "marginTop": "auto",
            "padding": sidebar_clamp(2, 0.35, 4),
        },
    )


def build_density_control_panel(
    default_density_config,
    base_juvenile_mortality,
    base_adult_mortality,
    density_message="",
):
    helper_style = {
        "margin": "0",
        "color": "#cbd5e1",
        "fontSize": sidebar_clamp(7, 1.25, 11),
        "lineHeight": "1.3",
    }
    return html.Div(
        [
            html.P("Capacidad de Carga", className="sidebar-title", style={"margin": "0", "color": "white", "fontWeight": "700", "fontSize": sidebar_clamp(11, 2.1, 18)}),
            html.Div(
                [
                    seed_input("Umbral de Saturación por Celda", "saturation-threshold-input", default_density_config["saturation_threshold"]),
                    html.Div(
                        [
                            seed_input(
                                "Multiplicador Juvenil",
                                "juvenile-mortality-multiplier-input",
                                default_density_config["juvenile_mortality_multiplier"],
                            ),
                            html.P(
                                f"Tasa base juvenil: ({base_juvenile_mortality:.1%})",
                                style=helper_style,
                            ),
                        ],
                        style={"display": "grid", "gap": sidebar_clamp(2, 0.3, 4)}
                    ),
                    html.Div(
                        [
                            seed_input(
                                "Multiplicador Adulta",
                                "adult-mortality-multiplier-input",
                                default_density_config["adult_mortality_multiplier"],
                            ),
                            html.P(
                                f"Tasa base adulta: ({base_adult_mortality:.1%})",
                                style=helper_style,
                            ),
                        ],
                        style={"display": "grid", "gap": sidebar_clamp(2, 0.3, 4)}
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "flex-start",
                    "gap": sidebar_clamp(4, 0.65, 7),
                    "flex": "0 0 auto",
                    "minHeight": "auto",
                    "overflow": "visible",
                },
            ),
            html.Div(
                density_message,
                id="density-controls-message",
                style={"color": "#fecaca", "fontWeight": "700", "minHeight": 0, "fontSize": sidebar_clamp(8, 1.35, 12), "lineHeight": "1.2"},
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": sidebar_clamp(3, 0.45, 6),
            "padding": "0",
            "borderRadius": "0",
            "backgroundColor": "transparent",
            "border": "none",
            "boxShadow": "none",
            "minHeight": "auto",
            "height": "auto",
            "flex": "0 0 auto",
            "width": "100%",
            "overflow": "visible",
        },
    )


def build_environment_banner(temperature_range, salinity_range):
    temperature_min_c, temperature_max_c = temperature_range
    salinity_min, salinity_max = salinity_range
    temperature_text = "Sin datos"
    if temperature_min_c is not None and temperature_max_c is not None:
        temperature_text = f"{temperature_min_c:.1f} °C - {temperature_max_c:.1f} °C"

    salinity_text = "Sin datos"
    if salinity_min is not None and salinity_max is not None:
        salinity_text = f"{salinity_min:.2f} PSU - {salinity_max:.2f} PSU"

    return html.Div(
        [
            html.Span(
                " | ".join(
                    [
                        f"Temperatura en el área últimos 4 años: {temperature_text}",
                        "Umbral letal del pez león: ≤ 10 °C",
                        f"Salinidad del área últimos 4 años: {salinity_text}",
                        "Rango apto para colonización: 34.11 PSU - 38.11 PSU",
                    ]
                )
            ),
        ],
        style={
            "position": "absolute",
            "top": "0",
            "left": "0",
            "right": "0",
            "zIndex": "1100",
            "padding": f"{overlay_clamp(4, 0.7, 8)} {overlay_clamp(10, 1.8, 22)}",
            "backgroundColor": "rgba(8, 47, 73, 0.94)",
            "color": "white",
            "fontSize": overlay_width_clamp(10, 1, 10),
            "fontWeight": "700",
            "lineHeight": "1.25",
            "boxShadow": "0 6px 18px rgba(15, 23, 42, 0.24)",
            "overflow": "hidden",
            "textAlign": "center",
            "whiteSpace": "normal",
            "wordBreak": "normal",
            "overflowWrap": "anywhere",
        },
    )


def build_detail_panel(selected_cell_id, cells_by_id, build_current_detail, cell_state_label):
    if not selected_cell_id:
        detail_rows = [
            sidebar_section_title("Detalle de Celda"),
            html.P(
                "Selecciona una celda para ver su detalle.",
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "margin": "0",
                    "fontSize": sidebar_clamp(9, 1.65, 13),
                    "lineHeight": "1.18",
                    "color": "rgba(255, 255, 255, 0.78)",
                },
            ),
        ]
        return html.Div(detail_rows, style={**sidebar_content_grid_style(sidebar_row_count(detail_rows)), "color": "white"})

    cell = cells_by_id[selected_cell_id]
    colonizable_by_depth = cell.can_be_colonized()
    detail_rows = [
        sidebar_section_title(f"Detalle de Celda: {cell.cell_id}"),
        sidebar_stat("Estado", cell_state_label(cell.visible_state())),
        sidebar_stat("Profundidad", f"{cell.depth_m:.1f} m", "#15803d" if colonizable_by_depth else "#b91c1c"),
        sidebar_stat("Larvas", cell.total_larvae()),
        sidebar_stat("Peces León", cell.total_lionfish()),
        sidebar_stat("Juveniles", cell.total_juveniles()),
        sidebar_stat("Hembras adultas", cell.adult_females()),
        *build_current_detail(cell.cell_id),
    ]
    return html.Div(detail_rows, style={**sidebar_content_grid_style(sidebar_row_count(detail_rows)), "color": "white"})


def summary_category(text):
    return html.P(
        text,
        style={
            "margin": "0",
            "fontSize": sidebar_clamp(8, 1.25, 11),
            "fontWeight": "700",
            "letterSpacing": "0.07em",
            "textTransform": "uppercase",
            "color": "rgba(255, 255, 255, 0.45)",
            "lineHeight": "1.1",
            "alignSelf": "center",
        },
    )


def build_summary_panel(summary):
    return [
        sidebar_stat("Mes", summary["month"]),
        summary_category("Dispersión"),
        sidebar_stat("Celdas colonizadas", summary["colonized"]),
        sidebar_stat("Celdas con larvas", summary["larvae_cells"]),
        sidebar_stat("Celdas destino", summary["destination_cells"]),
        sidebar_stat("Rutas fuera de grilla", summary["routes_outside_grid"]),
        sidebar_stat("Celdas no colonizadas", summary["empty"]),
        summary_category("Población"),
        sidebar_stat("Peces León", summary["lionfish_units"]),
        sidebar_stat("Peces juveniles", summary["juvenile_units"]),
        sidebar_stat("Hembras adultas", summary["adult_females"]),
        sidebar_stat("Larvas en transporte", summary["larvae_units"]),
        summary_category("Pérdidas"),
        sidebar_stat("Muertes larvas", summary["dead_larvae"]),
        sidebar_stat("Muertes peces", summary["dead_lionfish"]),
    ]


def sidebar_summary_body_style(summary_rows):
    return {
        **sidebar_content_grid_style(len(summary_rows)),
        "flex": "1 1 0",
        "height": "auto",
        "overflowY": "auto",
        "overflowX": "hidden",
        "paddingRight": sidebar_clamp(3, 0.4, 6),
    }


def sidebar_summary_panel_style(summary_rows):
    return {
        "flex": "1 1 auto",
        "minHeight": "0",
        "height": "100%",
        "display": "flex",
        "flexDirection": "column",
        "overflow": "hidden",
        "padding": sidebar_clamp(10, 1.6, 18),
        "marginTop": "0",
        "borderRadius": sidebar_clamp(8, 1.5, 14),
        "backgroundColor": "rgba(15, 23, 42, 0.42)",
        "border": "1px solid rgba(255, 255, 255, 0.10)",
        "boxShadow": "inset 0 1px 0 rgba(255, 255, 255, 0.08)",
        "gap": sidebar_clamp(6, 0.9, 10),
    }


def build_sidebar_summary(summary_rows):
    summary_children = [
        sidebar_section_title("Resumen General"),
        html.Div(
            id="summary-body",
            children=summary_rows,
            className="seed-panel-scroll",
            style=sidebar_summary_body_style(summary_rows),
        ),
    ]
    return html.Div(
        summary_children,
        id="summary-panel",
        className="sidebar-panel sidebar-summary-panel",
        style=sidebar_summary_panel_style(summary_rows),
    )


def real_month_badge_style(currents_visible=False):
    return {
        "position": "absolute",
        "top": overlay_clamp(122, 15.2, 160) if currents_visible else overlay_clamp(82, 10.4, 118),
        "right": overlay_clamp(10, 1.8, 22),
        "zIndex": "1050",
        "display": "flex",
        "gap": overlay_clamp(7, 1.1, 12),
        "alignItems": "center",
        "padding": f"{overlay_clamp(8, 1.35, 14)} {overlay_clamp(10, 1.7, 18)}",
        "border": "1px solid rgba(255, 255, 255, 0.10)",
        "borderRadius": overlay_clamp(6, 0.9, 10),
        "backgroundColor": "rgba(0, 31, 63, 0.78)",
        "color": "white",
        "boxShadow": "0 6px 16px rgba(15, 23, 42, 0.16)",
        "fontSize": overlay_clamp(12, 1.85, 18),
        "fontWeight": "700",
        "lineHeight": "1",
        "pointerEvents": "none",
    }


def build_real_month_badge_children(real_month_label):
    return [
        html.Span("Mes Real:", style={"color": "rgba(255, 255, 255, 0.76)"}),
        html.Span(real_month_label),
    ]


def progress_shell_style():
    return {
        "position": "absolute",
        "left": "0",
        "right": "0",
        "bottom": "0",
        "height": PROGRESS_BAR_HEIGHT,
        "zIndex": "1500",
        "backgroundColor": "rgba(0, 31, 63, 0.60)",
        "borderTop": "1px solid rgba(255, 255, 255, 0.16)",
        "pointerEvents": "none",
    }


def build_simulation_progress_children(real_month_label, current_month, progress_target_month, progress_percent):
    return [
        html.Div(
            style={
                "height": "100%",
                "width": f"{progress_percent:.2f}%",
                "backgroundColor": "#38bdf8",
                "boxShadow": "0 0 10px rgba(56, 189, 248, 0.45)",
                "transition": "width 180ms ease",
            },
        ),
        html.Div(
            f"{real_month_label} · Mes {current_month} / {progress_target_month} · {progress_percent:.0f}%",
            style={
                "position": "absolute",
                "inset": "0",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "color": "white",
                "fontSize": overlay_clamp(9, 1.3, 13),
                "fontWeight": "700",
                "textShadow": "0 1px 3px rgba(15, 23, 42, 0.85)",
            },
        ),
    ]


def sidebar_style(is_open=True):
    return {
        "position": "absolute",
        "top": sidebar_clamp(30, 5, 42),
        "bottom": "calc(var(--bottom-bar-height) + 0px)",
        "left": "0",
        "zIndex": "1050",
        "width": "clamp(11rem, 22vw, 22rem)",
        "maxWidth": "92vw",
        "overflowX": "hidden",
        "overflowY": "auto",
        "padding": sidebar_clamp(8, 1.35, 14),
        "backgroundColor": "rgba(0, 31, 63, 0.72)",
        "color": "white",
        "fontSize": sidebar_clamp(9, 1.6, 14),
        "border": "1px solid rgba(255, 255, 255, 0.10)",
        "borderLeft": "none",
        "borderRadius": f"0 {sidebar_clamp(10, 1.8, 18)} {sidebar_clamp(10, 1.8, 18)} 0",
        "boxShadow": "6px 8px 28px rgba(15, 23, 42, 0.22)",
        "backdropFilter": "blur(12px) saturate(120%)",
        "WebkitBackdropFilter": "blur(12px) saturate(120%)",
        "transform": "translateX(0)" if is_open else "translateX(-100%)",
        "transition": "transform 180ms ease",
    }


def build_open_sidebar_button():
    return html.Button(
        "›",
        id="open-sidebar-btn",
        n_clicks=0,
        style={
            "position": "absolute",
            "top": "clamp(4rem, 12dvh, 6rem)",
            "left": "0",
            "zIndex": "1200",
            "padding": f"{sidebar_clamp(10, 1.7, 14)} {sidebar_clamp(8, 1.2, 11)}",
            "border": "1px solid rgba(255, 255, 255, 0.10)",
            "borderLeft": "none",
            "borderRadius": f"0 {sidebar_clamp(8, 1.5, 13)} {sidebar_clamp(8, 1.5, 13)} 0",
            "backgroundColor": "rgba(0, 31, 63, 0.78)",
            "color": "white",
            "cursor": "pointer",
            "fontSize": sidebar_clamp(14, 2.2, 20),
            "fontWeight": "700",
            "lineHeight": "1",
        },
    )


def build_sidebar(
    selected_cell_id,
    detail_content,
    summary_rows,
    lat_lines,
    lon_lines,
    sidebar_title_asset_name="Titulo.png",
):
    close_button = html.Button(
        "«",
        id="close-sidebar-btn",
        n_clicks=0,
        style={
            **button_style("rgba(255,255,255,0.12)", "white"),
            "width": sidebar_clamp(24, 4, 34),
            "height": sidebar_clamp(22, 3.5, 30),
            "textAlign": "center",
            "justifyContent": "center",
            "padding": "0",
            "borderRadius": sidebar_clamp(4, 1, 8),
            "backgroundColor": "rgba(0, 31, 63, 0.78)",
            "border": "1px solid rgba(255, 255, 255, 0.10)",
        },
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Img(
                                src=f"/assets/{sidebar_title_asset_name}",
                                alt="Nereo",
                                className="sidebar-brand-image",
                                style={
                                    "width": "calc(80% )",
                                    "maxWidth": "none",
                                    "height": sidebar_clamp(65, 7, 80),
                                    "marginLeft": "-10px",
                                    "marginRight": "-10px",
                                    "objectFit": "cover",
                                    "objectPosition": "center",
                                    "display": "block",
                                    "flex": "0 1 auto",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "minWidth": "0",
                            "flex": "1 1 auto",
                            "overflow": "hidden",
                        },
                    ),
                    close_button,
                ],
                style={
                    "flex": "0 1 auto",
                    "minHeight": "0",
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "gap": sidebar_clamp(7, 1.15, 12),
                    "overflow": "hidden",
                },
            ),
            build_sidebar_controls(),
            html.Div(
                [
                    html.Button(
                        "Resumen General",
                        id="sidebar-summary-tab",
                        n_clicks=0,
                        type="button",
                        style=sidebar_tab_button_style(True),
                    ),
                    html.Button(
                        "Detalle de Celda",
                        id="sidebar-detail-tab",
                        n_clicks=0,
                        type="button",
                        style=sidebar_tab_button_style(False),
                    ),
                ],
                className="sidebar-tab-group",
                style=sidebar_tab_group_style(),
            ),
            html.Div(
                [
                    html.Div(
                        build_sidebar_summary(summary_rows),
                        id="summary-panel-container",
                        style=sidebar_panel_container_style(True),
                    ),
                    html.Div(
                        html.Div(
                            id="detail-body",
                            children=detail_content,
                            className="sidebar-panel sidebar-detail-panel seed-panel-scroll",
                            style=sidebar_detail_panel_style(detail_content),
                        ),
                        id="detail-panel-container",
                        style=sidebar_panel_container_style(False),
                    ),
                    build_save_simulation_button(),
                ],
                id="sidebar-fit-area",
                className="sidebar-fit-area",
                style=sidebar_fit_area_style(detail_content, summary_rows),
            ),
        ],
        className="app-sidebar",
        style={
            "height": "100%",
            "display": "flex",
            "flexDirection": "column",
            "justifyContent": "space-between",
            "gap": sidebar_clamp(7, 1.1, 13),
            "minHeight": "0",
            "overflow": "hidden",
        },
    )
