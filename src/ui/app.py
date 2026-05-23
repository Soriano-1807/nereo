import base64
import os
import uuid
from threading import Lock

import dash_leaflet as dl
from dash import Dash, dcc, html
from dash_extensions import EventListener
from flask import has_request_context, session

from src.application.services import SimulationService
from src.ui.callbacks_manager import CallbacksManager, DashboardConfig
from src.ui.components.map_view import (
    build_colonizable_boundary_layers,
    build_current_layer_group,
    build_floating_legends_help,
    build_grid_layers,
    build_map_view_controls,
    build_selection_polygon,
)
from src.ui.components.config_panel import build_config_panel
from src.ui.components.sidebar import (
    build_density_control_panel,
    build_detail_panel,
    build_open_sidebar_button,
    build_real_month_badge_children,
    build_sidebar,
    build_simulation_progress_children,
    build_summary_panel,
    progress_shell_style,
    real_month_badge_style,
    sidebar_style,
)


LON_LINES = [-69.8, -69.7, -69.6, -69.5, -69.4, -69.3, -69.2, -69.1, -69.0, -68.9, -68.8, -68.7, -68.6, -68.5, -68.4, -68.3, -68.2, -68.1, -68.0, -67.9, -67.8, -67.7, -67.6,
    -67.5, -67.4, -67.3, -67.2, -67.1, -67.0, -66.9, -66.8, -66.7, -66.6, -66.5, -66.4, -66.3, -66.2, -66.1, -66.0, -65.9, -65.8, -65.7, -65.6, -65.5, -65.4, -65.3, -65.2, -65.1, -65.0, -64.9, -64.8, -64.7]
LAT_LINES = [
    12.0, 11.9, 11.8, 11.7, 11.6, 11.5, 11.4, 11.3, 11.2, 11.1, 11.0, 10.9, 10.8, 10.7, 10.6, 10.5, 10.4, 10.3, 10.2, 10.1
]
MAP_BOUNDS = [[7.0, -76.98652227295615], [15.0, -57.51347772704384]]
KEYBOARD_EVENTS = [{"event": "keydown", "props": ["key"]}]
SIDEBAR_TITLE_ASSET_NAME = "Titulo.png"
FAVICON_ASSET_NAME = "favicon.png"


def build_grid_navigation_data(grid):
    return {
        "rows": grid.rows,
        "cols": grid.cols,
    }


def build_grid_selection_positions(features_by_id):
    return {
        cell_id: feature["positions"]
        for cell_id, feature in features_by_id.items()
    }


class NereoApp:
    def __init__(self, lon_lines=None, lat_lines=None):
        self.lon_lines = lon_lines or LON_LINES
        self.lat_lines = lat_lines or LAT_LINES
        self.config = DashboardConfig()
        self._services_by_session: dict[str, SimulationService] = {}
        self._default_service: SimulationService | None = None
        self._services_lock = Lock()
        self.app = Dash(__name__, suppress_callback_exceptions=True, title="Nereo", update_title=None)
        self.app.server.secret_key = os.getenv("SECRET_KEY", "nereo-session-secret")
        self.callbacks_manager = CallbacksManager(self.app, self.get_service, self.config)
        self.app.index_string = self._build_index_string()
        self.app.layout = self.build_layout
        self.callbacks_manager.register()

    def _build_service(self) -> SimulationService:
        return SimulationService(self.lon_lines, self.lat_lines)

    def _get_session_id(self) -> str | None:
        if not has_request_context():
            return None

        session_id = session.get("nereo_session_id")
        if not session_id:
            session_id = uuid.uuid4().hex
            session["nereo_session_id"] = session_id
        return session_id

    def get_service(self) -> SimulationService:
        session_id = self._get_session_id()
        with self._services_lock:
            if session_id is None:
                if self._default_service is None:
                    self._default_service = self._build_service()
                return self._default_service

            service = self._services_by_session.get(session_id)
            if service is None:
                service = self._build_service()
                self._services_by_session[session_id] = service
            return service

    def _build_index_string(self):
        favicon_url = self.app.get_asset_url(FAVICON_ASSET_NAME)
        loading_asset_path = os.path.join(self.app.config.assets_folder, "Cargando....png")
        with open(loading_asset_path, "rb") as loading_asset_file:
            loading_background_data_url = (
                "data:image/png;base64," + base64.b64encode(loading_asset_file.read()).decode("ascii")
            )
        return f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        <link rel="icon" type="image/png" sizes="512x512" href="{favicon_url}">
        <link rel="apple-touch-icon" href="{favicon_url}">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background: #001f3f url("{loading_background_data_url}") center center / cover no-repeat;
            }}

            #react-entry-point,
            #_dash-app-content {{
                width: 100%;
                height: 100%;
                background: transparent;
            }}

            #react-entry-point ._dash-loading {{
                position: fixed;
                inset: 0;
                background: #001f3f url("{loading_background_data_url}") center center / cover no-repeat;
                color: transparent !important;
                font-size: 0 !important;
                line-height: 0 !important;
                text-indent: -9999px;
                overflow: hidden;
                white-space: nowrap;
                width: 100vw;
                height: 100vh;
            }}
        </style>
        {{%css%}}
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""

    def get_real_month_label(self):
        return self.callbacks_manager.get_real_month_label()

    def get_progress_percent(self):
        return self.callbacks_manager.get_progress_percent()

    def build_layout(self):
        service = self.get_service()
        service.reset_simulation()
        default_density_config = service.default_density_config().as_dict()
        current_speed_min, current_speed_max = service.current_speed_range
        summary_rows = build_summary_panel(service.get_summary())
        detail_content = build_detail_panel(
            self.config.default_selected_cell,
            service.cells_by_id,
            self.callbacks_manager.build_current_detail,
            self.callbacks_manager.cell_state_label,
        )
        density_panel = build_density_control_panel(
            default_density_config,
            service.juvenile_mortality_rate,
            service.adult_mortality_rate,
        )
        real_month_label = self.get_real_month_label()
        progress_percent = self.get_progress_percent()
        progress_target_month = self.callbacks_manager.get_progress_target_month()

        return EventListener(
            id="keyboard-listener",
            events=KEYBOARD_EVENTS,
            children=html.Div(
                [
                    dcc.Store(id="selected-cell-store", data=self.config.default_selected_cell),
                    dcc.Store(id="sidebar-visible-store", data=False),
                    dcc.Store(id="sidebar-active-panel-store", data="summary"),
                    dcc.Store(id="currents-visible-store", data=False),
                    dcc.Store(id="transport-visible-store", data=False),
                    dcc.Store(id="sim-version-store", data=0),
                    dcc.Store(id="seed-active-store", data=True),
                    dcc.Store(id="seed-mode", data=self.config.default_seed_mode),
                    dcc.Store(id="seed-draft-store", data={}),
                    dcc.Store(id="density-config-store", data=default_density_config),
                    dcc.Store(id="loaded-simulation-store", data=False),
                    dcc.Store(id="seed-input-source-store", data=self.config.default_selected_cell),
                    dcc.Store(id="grid-navigation-store", data=build_grid_navigation_data(service.grid)),
                    dcc.Store(id="grid-selection-positions-store", data=build_grid_selection_positions(service.features_by_id)),
                    dcc.Store(id="loading-pending-action-store", data=None),
                    dcc.Store(id="current-marker-target-store", data={"target": 0, "batchClass": None}),
                    dcc.Download(id="simulation-download"),
                    html.Div(
                        [
                            build_map_view_controls(),
                            html.Div(
                                [
                                    html.Div(id="app-loading-signal", style={"display": "none"}),
                                    html.Div(
                                        [
                                            html.Span(className="app-loading-custom-spinner"),
                                            html.Span("Cargando...", className="app-loading-label"),
                                        ],
                                        id="custom-global-loader",
                                        className="app-loading-indicator",
                                        style={"display": "none"},
                                    ),
                                ],
                                style={"position": "absolute", "inset": "0", "pointerEvents": "none", "zIndex": 1000},
                            ),
                            dl.Map(
                                id="map",
                                center=[
                                    (service.grid.south + service.grid.north) / 2,
                                    service.grid.west + ((service.grid.east - service.grid.west) * 0.33),
                                ],
                                zoom=7.8,
                                minZoom=6.0,
                                maxZoom=10.0,
                                zoomSnap=0.25,
                                zoomDelta=0.25,
                                wheelPxPerZoomLevel=90,
                                scrollWheelZoom=True,
                                touchZoom=True,
                                dragging=True,
                                doubleClickZoom=True,
                                boxZoom=True,
                                keyboard=False,
                                zoomControl=False,
                                maxBounds=MAP_BOUNDS,
                                maxBoundsViscosity=0.85,
                                children=[
                                    dl.TileLayer(
                                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                                        attribution="Tiles © Esri",
                                    ),
                                    dl.ZoomControl(position="bottomright"),
                                    dl.LayerGroup(id="grid-layer", children=build_grid_layers(service.grid_features, service.cells_by_id)),
                                    dl.LayerGroup(
                                        id="colonizable-boundary-layer",
                                        children=build_colonizable_boundary_layers(service.grid_features, service.colonizable_feature_ids),
                                    ),
                                    dl.LayerGroup(id="seed-draft-layer", children=[]),
                                    dl.Pane(
                                        name="currents-pane",
                                        children=html.Div(
                                            id="current-layer-container",
                                            children=build_current_layer_group(
                                                False,
                                                0,
                                                service.get_environment_month(),
                                                service.grid_features,
                                                service.get_current_for_cell,
                                                current_speed_min,
                                                current_speed_max,
                                            ),
                                        ),
                                        style={"zIndex": 410},
                                    ),
                                    dl.Pane(
                                        name="transport-pane",
                                        children=dl.LayerGroup(id="transport-path-layer", children=[]),
                                        style={"zIndex": 420},
                                    ),
                                    dl.LayerGroup(
                                        id="selection-layer",
                                        children=[build_selection_polygon(self.config.default_selected_cell, service.features_by_id)],
                                    ),
                                ],
                                style={"width": "100%", "height": "100%"},
                            ),
                            html.Div(
                                id="sidebar-container",
                                className="sidebar-shell custom-scrollbar",
                                children=build_sidebar(
                                    self.config.default_selected_cell,
                                    detail_content,
                                    summary_rows,
                                    self.lat_lines,
                                    self.lon_lines,
                                    SIDEBAR_TITLE_ASSET_NAME,
                                ),
                                style=sidebar_style(False),
                            ),
                            html.Div(
                                id="seed-panel-container",
                                children=build_config_panel(
                                    density_panel,
                                    self.config.default_selected_cell,
                                    {},
                                    self.config.default_seed_mode,
                                    SIDEBAR_TITLE_ASSET_NAME,
                                ),
                            ),
                            html.Div(id="open-sidebar-container", children=build_open_sidebar_button(), style={"display": "none"}),
                            html.Div(
                                id="floating-legends-help",
                                children=build_floating_legends_help(
                                    current_speed_min,
                                    current_speed_max,
                                    service.temperature_range,
                                    service.salinity_range,
                                ),
                            ),
                            html.Div(
                                id="real-month-badge",
                                children=build_real_month_badge_children(real_month_label),
                                style=real_month_badge_style(),
                            ),
                            html.Div(
                                id="simulation-progress",
                                children=build_simulation_progress_children(
                                    real_month_label,
                                    service.current_month,
                                    progress_target_month,
                                    progress_percent,
                                ),
                                style=progress_shell_style(),
                            ),
                        ],
                        style={"position": "relative", "height": "100vh", "width": "100%", "overflow": "hidden"},
                    ),
                ],
                style={"height": "100vh", "width": "100%", "margin": "0", "overflow": "hidden", "fontFamily": "Segoe UI, sans-serif"},
                tabIndex=0,
            ),
        )

dashboard = NereoApp()
app = dashboard.app
server = app.server
