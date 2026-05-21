from dash import dcc, html

from src.ui.components.sidebar import (
    SIDEBAR_BUTTON_STYLE,
    seed_input,
    sidebar_clamp,
    sidebar_logo_image_style,
    sidebar_logo_wrapper_style,
)


SEED_PANEL_BUTTON_STYLE = {
    **SIDEBAR_BUTTON_STYLE,
    "height": "auto",
    "justifyContent": "center",
    "textAlign": "center",
    "whiteSpace": "normal",
    "overflowWrap": "anywhere",
    "fontSize": sidebar_clamp(8, 1.35, 12),
    "padding": f"{sidebar_clamp(2, 0.45, 5)} {sidebar_clamp(4, 0.7, 8)}",
    "lineHeight": "1.1",
    "minWidth": "0",
    "width": "100%",
    "boxSizing": "border-box",
}

SEED_PANEL_CTA_BUTTON_STYLE = {
    **SEED_PANEL_BUTTON_STYLE,
    "fontWeight": "700",
}

CONFIG_PANEL_DIVIDER = "1px solid rgba(255, 255, 255, 0.10)"


def config_panel_card_style(has_divider=False):
    return {
        "display": "flex",
        "flexDirection": "column",
        "gap": sidebar_clamp(2, 0.35, 5),
        "padding": f"{sidebar_clamp(4, 0.65, 7)} {sidebar_clamp(5, 0.8, 8)}",
        "borderRadius": "0",
        "backgroundColor": "transparent",
        "border": "none",
        "borderBottom": CONFIG_PANEL_DIVIDER if has_divider else "none",
        "boxShadow": "none",
        "minHeight": "auto",
        "height": "auto",
        "flex": "0 0 auto",
        "overflow": "visible",
    }


def config_panel_unified_body_style():
    return {
        "flex": "0 0 auto",
        "minHeight": "auto",
        "height": "auto",
        "width": "88%",
        "maxWidth": "88%",
        "alignSelf": "center",
        "display": "flex",
        "flexDirection": "column",
        "overflow": "visible",
        "padding": sidebar_clamp(10, 1.6, 18),
        "marginTop": "auto",
        "marginBottom": "auto",
        "borderRadius": sidebar_clamp(8, 1.5, 14),
        "backgroundColor": "rgba(15, 23, 42, 0.42)",
        "border": "1px solid rgba(255, 255, 255, 0.10)",
        "boxShadow": "inset 0 1px 0 rgba(255, 255, 255, 0.08)",
        "gap": sidebar_clamp(6, 0.9, 10),
    }


def config_panel_middle_style():
    return {
        "flex": "1 1 auto",
        "minHeight": "0",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "stretch",
        "overflowY": "auto",
        "overflowX": "hidden",
        "padding": f"{sidebar_clamp(6, 1.0, 12)} 0",
    }


def seed_mode_button_style(is_active=False):
    return {
        **SEED_PANEL_BUTTON_STYLE,
        "backgroundColor": "rgba(56, 189, 248, 0.22)" if is_active else SIDEBAR_BUTTON_STYLE["backgroundColor"],
        "border": "1px solid rgba(56, 189, 248, 0.55)" if is_active else "1px solid rgba(255, 255, 255, 0.08)",
        "fontWeight": "700" if is_active else SIDEBAR_BUTTON_STYLE["fontWeight"],
        "fontSize": sidebar_clamp(8, 1.45, 13),
        "justifyContent": "center",
        "textAlign": "center",
        "whiteSpace": "normal",
        "overflowWrap": "anywhere",
        "opacity": "1" if is_active else "0.75",
    }


def seed_mode_box_style(is_visible):
    return {
        "display": "grid" if is_visible else "none",
        "gap": sidebar_clamp(3, 0.55, 7),
        "minHeight": "0",
    }


def build_seed_summary(seed_draft):
    seed_draft = seed_draft or {}
    adults = sum(values.get("adults", 0) for values in seed_draft.values())
    juveniles = sum(values.get("juveniles", 0) for values in seed_draft.values())
    larvae = sum(values.get("larvae", 0) for values in seed_draft.values())
    return f"Celdas: {len(seed_draft)} | Adultos: {adults} | Juveniles: {juveniles} | Larvas: {larvae}"


def get_seed_cell_values(cell_id, seed_draft):
    seed_draft = seed_draft or {}
    values = seed_draft.get(cell_id)
    if not values:
        return 0, 0, 0
    return (
        values.get("adults", 0),
        values.get("juveniles", 0),
        values.get("larvae", 0),
    )


def build_seed_cell_status(cell_id, seed_draft):
    adults, juveniles, larvae = get_seed_cell_values(cell_id, seed_draft)
    return f"Celda activa: {cell_id} | Adultos: {adults} | Juveniles: {juveniles} | Larvas: {larvae}"


def seed_values_match(a_adults, a_juveniles, a_larvae, b_adults, b_juveniles, b_larvae, parse_seed_input_for_match):
    return (
        parse_seed_input_for_match(a_adults) == b_adults
        and parse_seed_input_for_match(a_juveniles) == b_juveniles
        and parse_seed_input_for_match(a_larvae) == b_larvae
    )


def build_seed_brand(sidebar_title_asset_name="Titulo.png"):
    return html.Div(
        [
            html.Div(
                [
                    html.Img(
                        src=f"/assets/{sidebar_title_asset_name}",
                        alt="Nereo",
                        className="sidebar-brand-image sidebar-logo",
                        style=sidebar_logo_image_style(),
                    ),
                ],
                style={
                    **sidebar_logo_wrapper_style(),
                    "justifyContent": "center",
                    "width": "100%",
                },
            ),
        ],
        style={
            "flex": "0 1 auto",
            "flexShrink": "0",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
            "gap": sidebar_clamp(7, 1.15, 12),
            "overflow": "hidden",
            "width": "100%",
        },
        
    )


def build_seed_mode_selector(active_mode="assisted"):
    return html.Div(
        [
            html.Button("Inicio aleatorio", id="seed-mode-random-btn", n_clicks=0, className="sidebar-button", style=seed_mode_button_style(active_mode == "random")),
            html.Button("Definir celda por celda", id="seed-mode-manual-btn", n_clicks=0, className="sidebar-button", style=seed_mode_button_style(active_mode == "manual")),
            html.Button("Asistido", id="seed-mode-assisted-btn", n_clicks=0, className="sidebar-button", style=seed_mode_button_style(active_mode == "assisted")),
        ],
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(68px, 1fr))",
            "gap": sidebar_clamp(3, 0.55, 7),
        },
    )


def build_simulation_upload_panel():
    return html.Div(
        [
            html.P(
                "Cargar simulacion guardada",
                style={"margin": "0", "color": "white", "fontWeight": "700", "fontSize": sidebar_clamp(11, 2.1, 18)},
            ),
            dcc.Upload(
                id="simulation-upload",
                accept=".csv,text/csv",
                children=html.Div(
                    "Buscar archivo CSV",
                    id="simulation-upload-btn",
                    style=SEED_PANEL_BUTTON_STYLE,
                ),
                style={"width": "100%", "display": "block"},
                multiple=False,
            ),
            html.Div(
                id="simulation-upload-message",
                style={
                    "color": "#bfdbfe",
                    "fontWeight": "700",
                    "minHeight": sidebar_clamp(6, 1.0, 12),
            "fontSize": sidebar_clamp(8, 1.25, 12),
                    "lineHeight": "1.15",
                },
            ),
        ],
        style={
            **config_panel_card_style(has_divider=True),
            "paddingBottom": sidebar_clamp(4, 0.6, 6),
        },
    )


def build_seed_mode_content(selected_cell_id, seed_draft, seed_mode="assisted"):
    return html.Div(
        [
            html.Div(
                [
                    html.P(
                        "Inicio aleatorio usa la probabilidad base para poblar peces y larvas en la grilla.",
                        style={"margin": "0", "color": "white", "fontSize": sidebar_clamp(8, 1.45, 13), "lineHeight": "1.2"},
                    ),
                ],
                id="seed-random-box",
                style=seed_mode_box_style(seed_mode == "random"),
            ),
            html.Div(
                [
                    html.P(
                        "Selecciona una celda, escribe unidades y guarda.",
                        style={"margin": "0", "color": "white", "fontSize": sidebar_clamp(8, 1.45, 13), "lineHeight": "1.2"},
                    ),
                    html.Div(
                        id="seed-selected-cell",
                        children=build_seed_cell_status(selected_cell_id, seed_draft),
                        style={"color": "#bfdbfe", "fontWeight": "700", "fontSize": sidebar_clamp(10, 1.85, 16)},
                    ),
                    html.Div(
                        [
                            seed_input("Adultos", "seed-cell-adults", get_seed_cell_values(selected_cell_id, seed_draft)[0], compact=True),
                            seed_input("Juveniles", "seed-cell-juveniles", get_seed_cell_values(selected_cell_id, seed_draft)[1], compact=True),
                            seed_input("Larvas", "seed-cell-larvae", get_seed_cell_values(selected_cell_id, seed_draft)[2], compact=True),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                            "gap": sidebar_clamp(2, 0.45, 6),
                        },
                    ),
                    html.Div(
                        [
                            html.Button("Guardar celda", id="seed-save-cell-btn", n_clicks=0, style=SEED_PANEL_BUTTON_STYLE),
                            html.Button("Limpiar celda", id="seed-clear-cell-btn", n_clicks=0, style=SEED_PANEL_BUTTON_STYLE),
                            html.Button("Limpiar grilla", id="seed-clear-btn", n_clicks=0, style=SEED_PANEL_BUTTON_STYLE),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(64px, 1fr))",
                            "gap": sidebar_clamp(2, 0.45, 6),
                        },
                    ),
                    html.Div(
                        id="seed-draft-summary",
                        children=build_seed_summary(seed_draft),
                        style={"color": "white", "fontSize": sidebar_clamp(8, 1.55, 14), "lineHeight": "1.2"},
                    ),
                ],
                id="seed-manual-box",
                style=seed_mode_box_style(seed_mode in {"manual", "assisted"}),
            ),
            html.Div(
                [
                    html.P(
                        "Asistido define el resto.",
                        style={"margin": "0", "color": "white", "fontSize": sidebar_clamp(8, 1.45, 13), "lineHeight": "1.2"},
                    ),
                ],
                id="seed-assisted-box",
                style=seed_mode_box_style(seed_mode == "assisted"),
            ),
        ],
        id="seed-mode-content",
        style={
            "display": "grid",
            "gap": sidebar_clamp(3, 0.55, 7),
            "minHeight": "0",
        },
    )


def config_panel_style():
    return {
        "position": "absolute",
        "top": "0",
        "bottom": "var(--bottom-bar-height)",
        "left": "0",
        "zIndex": "1050",
        "width": "clamp(13rem, 24vw, 24rem)",
        "maxWidth": "94vw",
        "height": "auto",
        "maxHeight": "none",
        "overflowX": "hidden",
        "overflowY": "hidden",
        "backgroundColor": "rgba(0, 31, 63, 0.46)",
        "color": "white",
        "border": "1px solid rgba(255, 255, 255, 0.10)",
        "borderLeft": "none",
        "borderRadius": f"0 {sidebar_clamp(10, 1.8, 18)} {sidebar_clamp(10, 1.8, 18)} 0",
        "boxShadow": "6px 8px 28px rgba(15, 23, 42, 0.22)",
        "backdropFilter": "blur(12px) saturate(120%)",
        "WebkitBackdropFilter": "blur(12px) saturate(120%)",
        "padding": sidebar_clamp(4, 0.65, 7),
        "fontSize": sidebar_clamp(9, 1.6, 14),
        "display": "flex",
        "flexDirection": "column",
        "gap": sidebar_clamp(12, 1.8, 20),
        "minHeight": "0",
        "overflow": "hidden",
        "boxSizing": "border-box",
    }


def build_config_panel(density_panel, selected_cell_id, seed_draft, seed_mode="assisted", sidebar_title_asset_name="Titulo.png"):
    return html.Div(
        [
            html.Div(
                [
                    build_seed_brand(sidebar_title_asset_name),
                ],
                style={
                    "flex": "0 0 auto",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "0",
                    "minHeight": "0",
                    "overflow": "hidden",
                },
            ),
            html.Div(
                [
                    html.Div(
                        [
                            build_simulation_upload_panel(),
                            html.Div(
                                id="density-control-panel",
                                children=density_panel,
                                style={
                                    **config_panel_card_style(has_divider=True),
                                    "minHeight": "auto",
                                    "overflow": "visible",
                                },
                            ),
                            html.Div(
                                [
                                    build_seed_mode_selector(seed_mode),
                                    build_seed_mode_content(selected_cell_id, seed_draft, seed_mode),
                                ],
                                style={
                                    **config_panel_card_style(),
                                    "minHeight": "4rem",
                                    "overflow": "visible",
                                },
                            ),
                        ],
                        style=config_panel_unified_body_style(),
                    ),
                ],
                className="seed-panel-scroll custom-scrollbar",
                style=config_panel_middle_style(),
            ),
            html.Div(
                [
                    html.Div(
                        id="seed-message",
                        style={
                            "color": "#fecaca",
                            "fontWeight": "700",
                            "minHeight": sidebar_clamp(5, 1.0, 10),
                            "fontSize": sidebar_clamp(9, 1.25, 14),
                            "lineHeight": "1.2",
                        },
                    ),
                    html.Button(
                        "Aplicar configuracion e iniciar",
                        id="seed-apply-btn",
                        n_clicks=0,
                        className="sidebar-button",
                        style={
                            **SEED_PANEL_CTA_BUTTON_STYLE,
                            "position": "relative",
                            "zIndex": "2",
                            "display": "flex",
                            "fontSize": sidebar_clamp(10, 1.55, 16),
                            "padding": f"{sidebar_clamp(5, 0.75, 9)} {sidebar_clamp(6, 0.9, 11)}",
                            "minHeight": sidebar_clamp(30, 4.2, 42),
                            "letterSpacing": "0",
                        },
                    ),
                ],
                style={
                    "flex": "0 0 auto",
                    "display": "grid",
                    "gap": sidebar_clamp(2, 0.25, 4),
                    "zIndex": "3",
                    "padding": "0",
                    "backgroundColor": "transparent",
                    "border": "none",
                    "boxShadow": "none",
                    "backdropFilter": "none",
                    "WebkitBackdropFilter": "none",
                },
            ),
        ],
        className="app-sidebar seed-panel-shell",
        style=config_panel_style(),
    )
