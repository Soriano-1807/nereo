import dash_leaflet as dl
from dash import html


GRID_STATE_STYLES = {
    "prohibida": {
        "color": "#111827",
        "weight": 1.2,
        "fillColor": "#111827",
        "fillOpacity": 0.55,
    },
    "colonizada": {
        "color": "#7f1d1d",
        "weight": 1.2,
        "fillColor": "#ef4444",
        "fillOpacity": 0.50,
    },
    "transporte": {
        "color": "#0f172a",
        "weight": 1.0,
        "fillColor": "#38bdf8",
        "fillOpacity": 0.35,
    },
    "no_colonizada": {
        "color": "#334155",
        "weight": 0.8,
        "fillColor": "#94a3b8",
        "fillOpacity": 0.08,
    },
}
GRID_STATE_ORDER = ["no_colonizada", "transporte", "colonizada", "prohibida"]
COLONIZABLE_BOUNDARY_STYLE = {
    "color": "#bae6fd",
    "weight": 2.7,
    "opacity": 0.95,
    "fillOpacity": 0,
}


def overlay_clamp(min_px, preferred_vmin, max_px):
    return f"clamp({min_px}px, {preferred_vmin}vmin, {max_px}px)"


def feature_center(feature):
    return feature["center"]


def current_arrow_color(speed, current_speed_min, current_speed_max):
    if current_speed_min is None or current_speed_max is None or current_speed_max == current_speed_min:
        return "#38bdf8"

    normalized = (speed - current_speed_min) / (current_speed_max - current_speed_min)
    if normalized < 0.33:
        return "#7dd3fc"
    if normalized < 0.66:
        return "#38bdf8"
    return "#0369a1"


def current_arrow_size(speed, current_speed_min, current_speed_max):
    if current_speed_min is None or current_speed_max is None or current_speed_max == current_speed_min:
        return 18

    normalized = (speed - current_speed_min) / (current_speed_max - current_speed_min)
    return 14 + (normalized * 16)


def direction_label(direction_degrees):
    directions = [
        "Este",
        "Este-noreste",
        "Noreste",
        "Norte-noreste",
        "Norte",
        "Norte-noroeste",
        "Noroeste",
        "Oeste-noroeste",
        "Oeste",
        "Oeste-suroeste",
        "Suroeste",
        "Sur-suroeste",
        "Sur",
        "Sur-sureste",
        "Sureste",
        "Este-sureste",
    ]
    index = round(direction_degrees / 22.5) % len(directions)
    return directions[index]


def positions_to_geojson_polygon(positions):
    return [[[lon, lat] for lat, lon in positions]]


def feature_collection(features):
    return {"type": "FeatureCollection", "features": features}


def build_cell_geojson_feature(feature, cell):
    return {
        "type": "Feature",
        "properties": {
            "id": cell.cell_id,
            "cell_id": cell.cell_id,
            "row": cell.row,
            "col": cell.col,
            "state": cell.visible_state(),
            "depth_m": cell.depth_m,
            "colonizable": cell.can_be_colonized(),
            "tooltip": f"Celda {cell.cell_id}",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": positions_to_geojson_polygon(feature["positions"]),
        },
    }


def build_current_layers(
    is_visible,
    environment_month,
    grid_features,
    get_current_for_cell,
    current_speed_min,
    current_speed_max,
):
    if not is_visible or environment_month is None:
        return []

    layers = []
    for feature in grid_features:
        current = get_current_for_cell(feature["id"], environment_month)
        if current is None:
            continue

        speed = current["speed"]
        direction = current["direction_degrees"]
        size = current_arrow_size(speed, current_speed_min, current_speed_max)
        color = current_arrow_color(speed, current_speed_min, current_speed_max)

        layers.append(
            dl.DivMarker(
                position=feature_center(feature),
                interactive=False,
                iconOptions={
                    "className": "current-arrow-marker",
                    "html": (
                        f"<div title='Corriente {speed:.3f} m/s, {direction:.1f}°' "
                        f"style='width:0;height:0;border-top:{size * 0.28}px solid transparent;"
                        f"border-bottom:{size * 0.28}px solid transparent;"
                        f"border-left:{size}px solid {color};"
                        f"filter:drop-shadow(0 1px 2px rgba(0,0,0,0.65));"
                        f"transform:rotate({-direction}deg);transform-origin:center;"
                        f"pointer-events:none;'></div>"
                    ),
                    "iconSize": [size, size],
                    "iconAnchor": [size / 2, size / 2],
                },
            )
        )

    return layers


def build_current_layer_group(
    is_visible,
    version,
    environment_month,
    grid_features,
    get_current_for_cell,
    current_speed_min,
    current_speed_max,
):
    return dl.LayerGroup(
        id={"type": "current-layer", "version": version},
        children=build_current_layers(
            is_visible,
            environment_month,
            grid_features,
            get_current_for_cell,
            current_speed_min,
            current_speed_max,
        ),
    )


def build_grid_layers(grid_features, cells_by_id, revision=None):
    features_by_state = {state: [] for state in GRID_STATE_ORDER}

    for feature in grid_features:
        cell = cells_by_id[feature["id"]]
        state = cell.visible_state()
        features_by_state.setdefault(state, []).append(build_cell_geojson_feature(feature, cell))

    layers = []
    for state in GRID_STATE_ORDER:
        state_features = features_by_state.get(state, [])
        if not state_features:
            continue

        layers.append(
            dl.GeoJSON(
                id={"type": "grid-geojson", "state": state},
                data=feature_collection(state_features),
                style=GRID_STATE_STYLES[state],
                interactive=True,
                bubblingMouseEvents=False,
                zoomToBoundsOnClick=False,
            )
        )

    return layers


def build_colonizable_boundary_layers(grid_features, colonizable_feature_ids):
    features = [
        {
            "type": "Feature",
            "properties": {
                "id": feature["id"],
                "cell_id": feature["id"],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": positions_to_geojson_polygon(feature["positions"]),
            },
        }
        for feature in grid_features
        if feature["id"] in colonizable_feature_ids
    ]

    if not features:
        return []

    return [
        dl.GeoJSON(
            id="colonizable-boundary-geojson",
            data=feature_collection(features),
            style=COLONIZABLE_BOUNDARY_STYLE,
            interactive=True,
            bubblingMouseEvents=False,
            zoomToBoundsOnClick=False,
        )
    ]


def build_selection_layer(selected_cell_id, features_by_id):
    if not selected_cell_id:
        return []

    feature = features_by_id.get(selected_cell_id)
    if feature is None:
        return []

    return [
        dl.Polygon(
            positions=feature["positions"],
            interactive=False,
            bubblingMouseEvents=False,
            pathOptions={
                "color": "#f8fafc",
                "weight": 5,
                "fillOpacity": 0,
            },
        )
    ]


def build_seed_draft_layer(seed_draft, features_by_id, revision=None):
    seed_draft = seed_draft or {}
    features = []

    for cell_id in seed_draft:
        feature = features_by_id.get(cell_id)
        if feature is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {"id": cell_id, "cell_id": cell_id},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": positions_to_geojson_polygon(feature["positions"]),
                },
            }
        )

    draft_revision = "|".join(
        sorted(
            f"{cell_id}:{values.get('adults', 0)}:{values.get('juveniles', 0)}:{values.get('larvae', 0)}"
            for cell_id, values in seed_draft.items()
        )
    )

    return [
        dl.GeoJSON(
            id="seed-draft-geojson",
            data=feature_collection(features),
            style={"color": "#22c55e", "weight": 2, "fillColor": "#22c55e", "fillOpacity": 0.35},
            interactive=True,
            bubblingMouseEvents=True,
            hideout={"revision": draft_revision},
            zoomToBoundsOnClick=False,
        )
    ]


def build_transport_path_layers(transport_events, features_by_id, cells_by_id, revision=None):
    layers = []

    for index, event in enumerate(transport_events):
        event_data = event.as_dict() if hasattr(event, "as_dict") else event
        path = event_data.get("path", [])
        target_position = event_data.get("target_position")
        incoming_larvae = event_data.get("incoming_larvae")
        target_cell = cells_by_id.get(event_data.get("to"))
        route_settles = (
            target_position is not None
            and incoming_larvae is not None
            and target_cell is not None
            and target_cell.can_be_colonized()
        )
        route_color = "#22c55e" if route_settles else "#ef4444"
        if event_data.get("to") == "Fuera de grilla":
            route_status = "No se asienta: sale de la grilla"
        elif route_settles:
            route_status = "Se asienta"
        else:
            route_status = "No se asienta: celda no colonizable"
        positions = [
            feature_center(features_by_id[cell_id])
            for cell_id in path
            if cell_id in features_by_id
        ]
        if not positions:
            continue

        if len(positions) >= 2:
            layers.append(
                dl.Polyline(
                    positions=positions,
                    pathOptions={
                        "color": route_color,
                        "weight": 4,
                        "opacity": 0.95,
                    },
                )
            )

        layers.append(
            dl.CircleMarker(
                center=positions[0],
                radius=5,
                pathOptions={
                    "color": route_color,
                    "fillColor": "#ffffff",
                    "fillOpacity": 0.0,
                    "weight": 2,
                },
            )
        )

        layers.append(
            dl.CircleMarker(
                center=positions[-1],
                radius=4,
                pathOptions={
                    "color": route_color,
                    "fillColor": route_color,
                    "fillOpacity": 0.95,
                    "weight": 1,
                },
                children=[
                    dl.Tooltip(
                        f"{route_status}: {event_data['from']} -> {event_data['to']} ({len(path) - 1} subpasos)",
                        direction="top",
                    )
                ],
            )
        )

    return layers


def build_floating_legends_help(current_speed_min=None, current_speed_max=None):
    return html.Div(
        [
            html.Button(
                "i",
                className="legend-info-button",
                title="Ver leyendas",
                type="button",
                **{"aria-label": "Ver leyendas"},
            ),
            html.Div(
                [
                    html.Div("Leyendas", className="legend-info-heading"),
                    html.Div(
                        [
                            build_grid_legend_help_section(),
                            build_current_legend_help_section(current_speed_min, current_speed_max),
                            build_transport_legend_help_section(),
                        ],
                        className="legend-info-content",
                    ),
                ],
                className="legend-info-popover",
                role="tooltip",
            ),
        ],
        className="legend-info-shell",
    )


def build_grid_legend_help_section():
    return legend_help_section(
        "Celdas",
        [
            square_legend_help_item("#ef4444", "Colonizada"),
            square_legend_help_item("#38bdf8", "Solo larvas"),
            square_legend_help_item("#94a3b8", "No colonizada"),
            square_legend_help_item("transparent", "Colonizable", border="2px solid #38bdf8"),
            square_legend_help_item("#111827", "Prohibida"),
        ],
    )


def build_current_legend_help_section(current_speed_min, current_speed_max):
    if current_speed_min is None or current_speed_max is None:
        return legend_help_section(
            "Corrientes",
            [
                square_legend_help_item("#7dd3fc", "Baja"),
                square_legend_help_item("#38bdf8", "Media"),
                square_legend_help_item("#0369a1", "Alta"),
            ],
        )

    low_limit = current_speed_min + ((current_speed_max - current_speed_min) * 0.33)
    high_limit = current_speed_min + ((current_speed_max - current_speed_min) * 0.66)

    return legend_help_section(
        "Corrientes",
        [
            square_legend_help_item("#7dd3fc", f"Baja: <= {low_limit:.3f} m/s"),
            square_legend_help_item("#38bdf8", f"Media: {low_limit:.3f} a {high_limit:.3f} m/s"),
            square_legend_help_item("#0369a1", f"Alta: >= {high_limit:.3f} m/s"),
        ],
    )


def build_transport_legend_help_section():
    return legend_help_section(
        "Transporte",
        [
            line_legend_help_item("#22c55e", "Larva se asienta en la grilla"),
            line_legend_help_item("#ef4444", "Larva sale de la grilla"),
        ],
    )


def legend_help_section(title, items):
    return html.Div(
        [
            html.Div(title, className="legend-info-title"),
            html.Div(items, className="legend-info-list"),
        ],
        className="legend-info-section",
    )


def square_legend_help_item(color, label, border=None):
    return html.Div(
        [
            html.Span(
                className="legend-info-swatch",
                style={
                    "backgroundColor": color,
                    "border": border or "none",
                },
            ),
            html.Span(label, className="legend-info-label"),
        ],
        className="legend-info-item",
    )


def line_legend_help_item(color, label):
    return html.Div(
        [
            html.Span(
                className="legend-info-line",
                style={"backgroundColor": color},
            ),
            html.Span(label, className="legend-info-label"),
        ],
        className="legend-info-item",
    )


def build_map_view_controls():
    text_button_style = {
        "padding": "0",
        "border": "none",
        "backgroundColor": "transparent",
        "color": "white",
        "cursor": "pointer",
        "fontSize": overlay_clamp(11, 1.55, 16),
        "fontWeight": "600",
        "textShadow": "0 1px 4px rgba(15, 23, 42, 0.75)",
    }

    return html.Div(
        [
            html.Button("Area de estudio", id="focus-grid-btn", n_clicks=0, style=text_button_style),
            html.Button("Costa de Venezuela", id="focus-coast-btn", n_clicks=0, style=text_button_style),
        ],
        style={
            "position": "absolute",
            "top": overlay_clamp(34, 4.6, 52),
            "left": "50%",
            "transform": "translateX(-50%)",
            "zIndex": "1050",
            "display": "flex",
            "gap": overlay_clamp(10, 1.65, 20),
            "alignItems": "center",
            "padding": f"{overlay_clamp(5, 0.9, 10)} {overlay_clamp(9, 1.45, 16)}",
            "border": "1px solid rgba(255, 255, 255, 0.10)",
            "borderRadius": overlay_clamp(6, 0.9, 10),
            "backgroundColor": "rgba(0, 31, 63, 0.78)",
            "boxShadow": "0 6px 16px rgba(15, 23, 42, 0.16)",
        },
    )
