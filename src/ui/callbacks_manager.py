import base64
from dataclasses import dataclass

from dash import ALL, Input, Output, State, ctx, dcc, no_update

from src.domain.sim_config import DensityMortalityConfig
from src.infrastructure.sim_csv_codec import SimulationCsvSerializer
from src.ui.components.map_view import (
    build_current_layer_group,
    build_grid_layers,
    build_seed_draft_layer,
    build_selection_layer,
    build_transport_path_layers,
)
from src.ui.components.config_panel import (
    build_seed_cell_status,
    build_seed_summary,
    get_seed_cell_values,
    seed_mode_box_style,
    seed_mode_button_style,
    seed_values_match,
)
from src.ui.components.sidebar import (
    SIDEBAR_PANEL_DETAIL,
    SIDEBAR_PANEL_SUMMARY,
    build_detail_panel,
    build_real_month_badge_children,
    build_simulation_progress_children,
    build_summary_panel,
    progress_shell_style,
    real_month_badge_style,
    sidebar_detail_panel_style,
    sidebar_fit_area_style,
    sidebar_panel_container_style,
    sidebar_style,
    sidebar_summary_body_style,
    sidebar_summary_panel_style,
    sidebar_tab_button_style,
)
from src.utils.parsing import parse_non_negative_int


@dataclass(frozen=True)
class DashboardConfig:
    default_selected_cell: str = "A1"
    real_month_names: tuple[str, ...] = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    real_month_start_year: int = 2026


class CallbacksManager:
    def __init__(self, app, service_getter, config: DashboardConfig | None = None):
        self.app = app
        self._service_getter = service_getter
        self.config = config or DashboardConfig()
        self.csv_serializer = SimulationCsvSerializer()

    @property
    def service(self):
        return self._service_getter()

    def get_real_month_label(self):
        month_offset = self.service.current_month
        month_index = month_offset % 12
        year = self.config.real_month_start_year + (month_offset // 12)
        return f"{self.config.real_month_names[month_index]} {year}"

    def get_progress_target_month(self):
        return self.service.simulation_parameters.max_simulation_month

    def get_progress_percent(self):
        progress_target_month = self.get_progress_target_month()
        if progress_target_month <= 0:
            return 0
        return min(100, max(0, (self.service.current_month / progress_target_month) * 100))

    def build_current_detail(self, cell_id):
        environment_month = self.service.get_environment_month()
        current = self.service.get_current_for_cell(cell_id, environment_month)
        from src.ui.components.sidebar import sidebar_stat

        if current is None:
            return [sidebar_stat("Corriente", "Sin datos")]

        from src.ui.components.map_view import direction_label
        return [
            sidebar_stat("Corriente", environment_month),
            sidebar_stat("Direccion", direction_label(current["direction_degrees"])),
            sidebar_stat("Intensidad", f"{current['speed']:.3f} m/s"),
        ]

    def cell_state_label(self, state):
        labels = {
            "no_colonizada": "No Colonizada",
            "colonizada": "Colonizada",
            "transporte": "Transporte",
            "prohibida": "Prohibida",
        }
        return labels.get(state, str(state).replace("_", " ").title())

    def _move_cell_selection(self, current_cell_id: str | None, key: str) -> str | None:
        grid = self.service.grid
        if key not in {"ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"}:
            return current_cell_id
        if current_cell_id is None:
            return "A1"

        cell = grid.cells_by_id[current_cell_id]
        row, col = cell.row, cell.col

        if key == "ArrowUp":
            row = max(0, row - 1)
        elif key == "ArrowDown":
            row = min(grid.rows - 1, row + 1)
        elif key == "ArrowLeft":
            col = max(0, col - 1)
        elif key == "ArrowRight":
            col = min(grid.cols - 1, col + 1)

        next_cell = grid.get_cell(row, col)
        return next_cell.cell_id if next_cell else current_cell_id

    def decode_upload_contents(self, contents: str) -> str:
        if not contents or "," not in contents:
            raise ValueError("No se pudo leer el archivo CSV.")
        encoded = contents.split(",", 1)[1]
        return base64.b64decode(encoded).decode("utf-8-sig")

    def density_config_from_store(self, density_config: dict | None) -> DensityMortalityConfig:
        density_config = density_config or self.service.default_density_config().as_dict()
        return DensityMortalityConfig(
            saturation_threshold=density_config["saturation_threshold"],
            juvenile_mortality_multiplier=density_config["juvenile_mortality_multiplier"],
            adult_mortality_multiplier=density_config["adult_mortality_multiplier"],
        )

    def register(self):
        app = self.app
        get_service = self._service_getter

        app.clientside_callback(
            """
            function(stepClicks, currentsClicks, transportClicks, seedApplyClicks, currentsVisible, transportVisible) {
                const triggered = dash_clientside.callback_context.triggered_id;
                if (!triggered) {
                    return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                }

                const buildPendingAction = function(action, targets) {
                    const requestId = `${action}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
                    window.__nereoLoadingRequestId = requestId;
                    return [true, { action, waitFor: targets, seen: {}, requestId }];
                };

                if (triggered === "step-btn") {
                    const waitFor = ["grid"];
                    if (currentsVisible) {
                        waitFor.push("currents");
                    }
                    if (transportVisible) {
                        waitFor.push("transport");
                    }
                    return buildPendingAction("step", waitFor);
                }

                if (triggered === "seed-apply-btn") {
                    const waitFor = ["grid"];
                    if (currentsVisible) {
                        waitFor.push("currents");
                    }
                    if (transportVisible) {
                        waitFor.push("transport");
                    }
                    return buildPendingAction("seed-apply", waitFor);
                }

                if (triggered === "toggle-currents-btn") {
                    return buildPendingAction("toggle-currents", ["currents"]);
                }

                if (triggered === "toggle-transport-btn") {
                    return buildPendingAction("toggle-transport", ["transport"]);
                }

                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            """,
            Output("loading-visible-store", "data"),
            Output("loading-pending-action-store", "data"),
            Input("step-btn", "n_clicks"),
            Input("toggle-currents-btn", "n_clicks"),
            Input("toggle-transport-btn", "n_clicks"),
            Input("seed-apply-btn", "n_clicks"),
            State("currents-visible-store", "data"),
            State("transport-visible-store", "data"),
            prevent_initial_call=True,
        )

        app.clientside_callback(
            """
            function(pendingAction) {
                if (!pendingAction || !pendingAction.requestId) {
                    return [window.dash_clientside.no_update, window.dash_clientside.no_update];
                }

                const requestId = pendingAction.requestId;
                window.__nereoLoadingRequestId = requestId;

                if (window.__nereoLoadingObserver) {
                    window.__nereoLoadingObserver.disconnect();
                    window.__nereoLoadingObserver = null;
                }
                if (window.__nereoLoadingQuietTimer) {
                    clearTimeout(window.__nereoLoadingQuietTimer);
                    window.__nereoLoadingQuietTimer = null;
                }
                if (window.__nereoLoadingMaxTimer) {
                    clearTimeout(window.__nereoLoadingMaxTimer);
                    window.__nereoLoadingMaxTimer = null;
                }

                return new Promise((resolve) => {
                    const finalize = () => {
                        if (window.__nereoLoadingRequestId !== requestId) {
                            resolve([window.dash_clientside.no_update, window.dash_clientside.no_update]);
                            return;
                        }

                        if (window.__nereoLoadingObserver) {
                            window.__nereoLoadingObserver.disconnect();
                            window.__nereoLoadingObserver = null;
                        }
                        if (window.__nereoLoadingQuietTimer) {
                            clearTimeout(window.__nereoLoadingQuietTimer);
                            window.__nereoLoadingQuietTimer = null;
                        }
                        if (window.__nereoLoadingMaxTimer) {
                            clearTimeout(window.__nereoLoadingMaxTimer);
                            window.__nereoLoadingMaxTimer = null;
                        }
                        window.__nereoLoadingRequestId = null;
                        resolve([false, null]);
                    };

                    const scheduleFinish = () => {
                        if (window.__nereoLoadingQuietTimer) {
                            clearTimeout(window.__nereoLoadingQuietTimer);
                        }
                        window.__nereoLoadingQuietTimer = setTimeout(() => {
                            requestAnimationFrame(() => {
                                requestAnimationFrame(finalize);
                            });
                        }, 400);
                    };

                    const mapRoot = document.getElementById("map");
                    if (!mapRoot) {
                        scheduleFinish();
                        window.__nereoLoadingMaxTimer = setTimeout(finalize, 6000);
                        return;
                    }

                    window.__nereoLoadingObserver = new MutationObserver(() => {
                        scheduleFinish();
                    });
                    window.__nereoLoadingObserver.observe(mapRoot, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                    });

                    mapRoot.addEventListener("layeradd", scheduleFinish, { once: true });
                    mapRoot.addEventListener("overlayadd", scheduleFinish, { once: true });
                    mapRoot.addEventListener("moveend", scheduleFinish, { once: true });

                    scheduleFinish();
                    window.__nereoLoadingMaxTimer = setTimeout(finalize, 6000);
                });
            }
            """,
            Output("loading-visible-store", "data", allow_duplicate=True),
            Output("loading-pending-action-store", "data", allow_duplicate=True),
            Input("loading-pending-action-store", "data"),
            prevent_initial_call=True,
        )

        app.clientside_callback(
            """
            function(isVisible) {
                return isVisible ? "app-loading-indicator" : "app-loading-indicator is-hidden";
            }
            """,
            Output("app-loading-indicator", "className"),
            Input("loading-visible-store", "data"),
        )

        @app.callback(
            Output("sim-version-store", "data"),
            Output("seed-active-store", "data"),
            Output("seed-mode", "data", allow_duplicate=True),
            Output("sidebar-visible-store", "data", allow_duplicate=True),
            Output("seed-draft-store", "data", allow_duplicate=True),
            Output("density-config-store", "data"),
            Output("loaded-simulation-store", "data"),
            Output("currents-visible-store", "data", allow_duplicate=True),
            Output("transport-visible-store", "data", allow_duplicate=True),
            Output("seed-message", "children"),
            Output("density-controls-message", "children"),
            Output("simulation-upload-message", "children"),
            Output("simulation-upload", "contents", allow_duplicate=True),
            Output("simulation-upload", "filename", allow_duplicate=True),
            Output("simulation-upload", "last_modified", allow_duplicate=True),
            Output("app-loading-signal", "children", allow_duplicate=True),
            Input("step-btn", "n_clicks"),
            Input("reset-btn", "n_clicks"),
            Input("seed-apply-btn", "n_clicks"),
            State("sim-version-store", "data"),
            State("seed-active-store", "data"),
            State("seed-mode", "data"),
            State("seed-draft-store", "data"),
            State("density-config-store", "data"),
            State("loaded-simulation-store", "data"),
            State("saturation-threshold-input", "value"),
            State("juvenile-mortality-multiplier-input", "value"),
            State("adult-mortality-multiplier-input", "value"),
            prevent_initial_call=True,
        )
        def advance_simulation(
            step_clicks,
            reset_clicks,
            apply_clicks,
            sim_version,
            seed_active,
            seed_mode,
            seed_draft,
            density_config,
            loaded_simulation,
            saturation_threshold,
            juvenile_mortality_multiplier,
            adult_mortality_multiplier,
        ):
            service = get_service()
            trigger = ctx.triggered_id
            sim_version = sim_version or 0
            seed_draft = seed_draft or {}
            density_config = density_config or service.default_density_config().as_dict()
            typed_density_config = self.density_config_from_store(density_config)
            loaded_simulation = bool(loaded_simulation)

            if trigger == "reset-btn":
                service.reset_simulation()
                return sim_version + 1, True, "assisted", False, {}, density_config, False, False, False, "", "", "", None, None, None, f"reset:{sim_version + 1}"

            if trigger == "step-btn":
                if seed_active:
                    return sim_version, True, no_update, no_update, seed_draft, density_config, loaded_simulation, no_update, no_update, "Aplica una semilla antes de avanzar.", "", no_update, no_update, no_update, no_update, no_update
                if not service.can_advance_simulation():
                    max_month = service.simulation_parameters.max_simulation_month
                    return sim_version, False, no_update, no_update, seed_draft, density_config, loaded_simulation, no_update, no_update, f"La simulacion no puede avanzar mas alla del mes {max_month}.", "", no_update, no_update, no_update, no_update, no_update
                service.apply_density_config(typed_density_config)
                service.step()
                return sim_version + 1, False, no_update, no_update, seed_draft, density_config, loaded_simulation, no_update, no_update, "", "", no_update, no_update, no_update, no_update, f"step:{sim_version + 1}"

            if trigger == "seed-apply-btn":
                if loaded_simulation:
                    return (
                        sim_version,
                        seed_active,
                        no_update,
                        no_update,
                        seed_draft,
                        density_config,
                        True,
                        no_update,
                        no_update,
                        "La simulacion cargada desde CSV no admite reconfiguracion inicial.",
                        "La simulacion cargada desde CSV no admite reconfiguracion de densidad.",
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )

                validated_density, density_error = service.validate_density_controls(
                    saturation_threshold,
                    juvenile_mortality_multiplier,
                    adult_mortality_multiplier,
                )
                if density_error:
                    return sim_version, seed_active, no_update, False, seed_draft, density_config, False, no_update, no_update, "", density_error, no_update, no_update, no_update, no_update, no_update

                density_config = validated_density.as_dict()
                service.apply_density_config(validated_density)

                if seed_mode == "random":
                    generated_seed = service.build_probabilistic_seed()
                    service.apply_seed(generated_seed)
                    return sim_version + 1, False, no_update, True, generated_seed, density_config, False, no_update, no_update, "", "", "", no_update, no_update, no_update, f"seed:{sim_version + 1}"

                if seed_mode == "manual":
                    error = service.validate_seed(seed_draft)
                    if error:
                        return sim_version, True, no_update, False, seed_draft, density_config, False, no_update, no_update, error, "", "", no_update, no_update, no_update, no_update
                    service.apply_seed(seed_draft)
                    return sim_version + 1, False, no_update, True, seed_draft, density_config, False, no_update, no_update, "", "", "", no_update, no_update, no_update, f"seed:{sim_version + 1}"

                if seed_mode == "assisted":
                    error = service.validate_seed(seed_draft) if seed_draft else None
                    if error:
                        return sim_version, True, no_update, False, seed_draft, density_config, False, no_update, no_update, error, "", "", no_update, no_update, no_update, no_update
                    assisted_seed = service.build_assisted_seed(seed_draft)
                    service.apply_seed(assisted_seed)
                    return sim_version + 1, False, no_update, True, assisted_seed, density_config, False, no_update, no_update, "", "", "", no_update, no_update, no_update, f"seed:{sim_version + 1}"

            return sim_version, seed_active, no_update, no_update, seed_draft, density_config, loaded_simulation, no_update, no_update, "", "", no_update, no_update, no_update, no_update, no_update

        @app.callback(
            Output("sim-version-store", "data", allow_duplicate=True),
            Output("seed-active-store", "data", allow_duplicate=True),
            Output("sidebar-visible-store", "data", allow_duplicate=True),
            Output("seed-draft-store", "data", allow_duplicate=True),
            Output("density-config-store", "data", allow_duplicate=True),
            Output("loaded-simulation-store", "data", allow_duplicate=True),
            Output("seed-message", "children", allow_duplicate=True),
            Output("density-controls-message", "children", allow_duplicate=True),
            Output("simulation-upload-message", "children", allow_duplicate=True),
            Output("saturation-threshold-input", "value", allow_duplicate=True),
            Output("juvenile-mortality-multiplier-input", "value", allow_duplicate=True),
            Output("adult-mortality-multiplier-input", "value", allow_duplicate=True),
            Output("simulation-upload", "contents", allow_duplicate=True),
            Output("simulation-upload", "filename", allow_duplicate=True),
            Output("simulation-upload", "last_modified", allow_duplicate=True),
            Input("simulation-upload", "contents"),
            State("simulation-upload", "filename"),
            State("sim-version-store", "data"),
            prevent_initial_call=True,
        )
        def load_simulation_from_csv(contents, filename, sim_version):
            service = get_service()
            if not contents:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

            try:
                csv_text = self.decode_upload_contents(contents)
                loaded_state = self.csv_serializer.load_into(service, csv_text)
            except ValueError as error:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, str(error), no_update, no_update, no_update, None, None, None

            density_config = loaded_state["density_config"]
            message = f"Simulacion cargada desde {filename or 'archivo.csv'}."
            next_version = (sim_version or 0) + 1
            return (
                next_version,
                False,
                True,
                {},
                density_config,
                True,
                "",
                "",
                message,
                density_config["saturation_threshold"],
                density_config["juvenile_mortality_multiplier"],
                density_config["adult_mortality_multiplier"],
                None,
                None,
                None,
            )

        @app.callback(
            Output("simulation-upload", "disabled"),
            Output("saturation-threshold-input", "disabled"),
            Output("juvenile-mortality-multiplier-input", "disabled"),
            Output("adult-mortality-multiplier-input", "disabled"),
            Output("seed-mode-random-btn", "disabled"),
            Output("seed-mode-manual-btn", "disabled"),
            Output("seed-mode-assisted-btn", "disabled"),
            Output("seed-cell-adults", "disabled"),
            Output("seed-cell-juveniles", "disabled"),
            Output("seed-cell-larvae", "disabled"),
            Output("seed-save-cell-btn", "disabled"),
            Output("seed-clear-cell-btn", "disabled"),
            Output("seed-clear-btn", "disabled"),
            Output("seed-apply-btn", "disabled"),
            Input("loaded-simulation-store", "data"),
        )
        def lock_initial_configuration(loaded_simulation):
            is_locked = bool(loaded_simulation)
            return (
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
                is_locked,
            )

        @app.callback(
            Output("seed-panel-container", "style"),
            Output("seed-random-box", "style"),
            Output("seed-manual-box", "style"),
            Output("seed-assisted-box", "style"),
            Output("seed-selected-cell", "children"),
            Output("seed-draft-summary", "children"),
            Input("seed-active-store", "data"),
            Input("seed-mode", "data"),
            Input("selected-cell-store", "data"),
            Input("seed-draft-store", "data"),
        )
        def render_config_panel(seed_active, seed_mode, selected_cell_id, seed_draft):
            return (
                {"display": "block" if seed_active else "none"},
                seed_mode_box_style(seed_mode == "random"),
                seed_mode_box_style(seed_mode in {"manual", "assisted"}),
                seed_mode_box_style(seed_mode == "assisted"),
                build_seed_cell_status(selected_cell_id, seed_draft),
                build_seed_summary(seed_draft),
            )

        @app.callback(
            Output("seed-mode", "data"),
            Output("seed-mode-random-btn", "style"),
            Output("seed-mode-manual-btn", "style"),
            Output("seed-mode-assisted-btn", "style"),
            Input("seed-mode-random-btn", "n_clicks"),
            Input("seed-mode-manual-btn", "n_clicks"),
            Input("seed-mode-assisted-btn", "n_clicks"),
            State("seed-mode", "data"),
            State("loaded-simulation-store", "data"),
            prevent_initial_call=True,
        )
        def update_seed_mode(random_clicks, manual_clicks, assisted_clicks, current_mode, loaded_simulation):
            next_mode = current_mode or "assisted"
            if loaded_simulation:
                return (
                    next_mode,
                    seed_mode_button_style(next_mode == "random"),
                    seed_mode_button_style(next_mode == "manual"),
                    seed_mode_button_style(next_mode == "assisted"),
                )

            trigger = ctx.triggered_id
            if trigger == "seed-mode-random-btn":
                next_mode = "random"
            elif trigger == "seed-mode-manual-btn":
                next_mode = "manual"
            elif trigger == "seed-mode-assisted-btn":
                next_mode = "assisted"
            return (
                next_mode,
                seed_mode_button_style(next_mode == "random"),
                seed_mode_button_style(next_mode == "manual"),
                seed_mode_button_style(next_mode == "assisted"),
            )

        @app.callback(
            Output("seed-apply-btn", "children"),
            Input("seed-mode", "data"),
        )
        def update_seed_apply_button(_seed_mode):
            return "Aplicar configuracion e iniciar"

        @app.callback(
            Output("seed-cell-adults", "value"),
            Output("seed-cell-juveniles", "value"),
            Output("seed-cell-larvae", "value"),
            Output("seed-input-source-store", "data"),
            Input("selected-cell-store", "data"),
            Input("seed-draft-store", "data"),
            State("seed-input-source-store", "data"),
            State("seed-cell-adults", "value"),
            State("seed-cell-juveniles", "value"),
            State("seed-cell-larvae", "value"),
        )
        def hydrate_seed_cell_inputs(selected_cell_id, seed_draft, source_cell_id, adults_value, juveniles_value, larvae_value):
            service = get_service()
            source_values = get_seed_cell_values(source_cell_id, seed_draft)
            if not seed_values_match(adults_value, juveniles_value, larvae_value, *source_values, service.parse_seed_input_for_match):
                return no_update, no_update, no_update, source_cell_id
            if selected_cell_id == source_cell_id:
                return no_update, no_update, no_update, source_cell_id
            selected_values = get_seed_cell_values(selected_cell_id, seed_draft)
            return selected_values[0], selected_values[1], selected_values[2], selected_cell_id

        @app.callback(
            Output("seed-draft-store", "data"),
            Output("seed-message", "children", allow_duplicate=True),
            Output("seed-cell-adults", "value", allow_duplicate=True),
            Output("seed-cell-juveniles", "value", allow_duplicate=True),
            Output("seed-cell-larvae", "value", allow_duplicate=True),
            Output("seed-input-source-store", "data", allow_duplicate=True),
            Input("seed-save-cell-btn", "n_clicks"),
            Input("seed-clear-cell-btn", "n_clicks"),
            Input("seed-clear-btn", "n_clicks"),
            State("selected-cell-store", "data"),
            State("seed-draft-store", "data"),
            State("seed-cell-adults", "value"),
            State("seed-cell-juveniles", "value"),
            State("seed-cell-larvae", "value"),
            State("loaded-simulation-store", "data"),
            prevent_initial_call=True,
        )
        def update_seed_draft(save_clicks, clear_cell_clicks, clear_clicks, selected_cell_id, seed_draft, adults, juveniles, larvae, loaded_simulation):
            service = get_service()
            if loaded_simulation:
                return seed_draft or {}, "La simulacion cargada desde CSV no admite cambios en la semilla.", no_update, no_update, no_update, no_update

            trigger = ctx.triggered_id
            if trigger == "seed-clear-btn":
                return {}, "", 0, 0, 0, selected_cell_id
            if trigger == "seed-clear-cell-btn":
                if selected_cell_id not in service.cells_by_id:
                    return seed_draft or {}, "Selecciona una celda valida.", no_update, no_update, no_update, no_update
                seed_draft = dict(seed_draft or {})
                seed_draft.pop(selected_cell_id, None)
                return seed_draft, "", 0, 0, 0, selected_cell_id

            adults = parse_non_negative_int(adults)
            juveniles = parse_non_negative_int(juveniles)
            larvae = parse_non_negative_int(larvae)
            if None in (adults, juveniles, larvae):
                return seed_draft or {}, "Revisa las cantidades.", no_update, no_update, no_update, no_update

            error = service.validate_seed({selected_cell_id: {"adults": adults, "juveniles": juveniles, "larvae": larvae}})
            if error:
                prefix = f"{selected_cell_id}: "
                if error.startswith(prefix):
                    error = error[len(prefix):]
                return seed_draft or {}, error, no_update, no_update, no_update, no_update

            seed_draft = dict(seed_draft or {})
            seed_draft[selected_cell_id] = {"adults": adults, "juveniles": juveniles, "larvae": larvae}
            return seed_draft, "", no_update, no_update, no_update, selected_cell_id

        @app.callback(
            Output("seed-draft-layer", "children"),
            Input("seed-active-store", "data"),
            Input("seed-draft-store", "data"),
        )
        def render_seed_draft_layer(seed_active, seed_draft):
            service = get_service()
            if not seed_active:
                return build_seed_draft_layer({}, service.features_by_id, revision="inactive")
            return build_seed_draft_layer(
                seed_draft,
                service.features_by_id,
                revision="|".join(sorted(seed_draft.keys())) or "empty",
            )

        @app.callback(
            Output("grid-layer", "children"),
            Input("sim-version-store", "data"),
        )
        def render_grid_layers(_sim_version):
            service = get_service()
            if not service.has_population():
                return build_grid_layers(
                    service.grid_features,
                    service.grid.empty_cells_by_id(),
                    revision=_sim_version,
                )
            return build_grid_layers(
                service.grid_features,
                service.cells_by_id,
                revision=_sim_version,
            )

        @app.callback(
            Output("transport-path-layer", "children"),
            Input("transport-visible-store", "data"),
            Input("sim-version-store", "data"),
        )
        def render_transport_path_layers(is_visible, _sim_version):
            service = get_service()
            if not is_visible:
                return []
            return build_transport_path_layers(
                service.get_transport_events(),
                service.features_by_id,
                service.cells_by_id,
                revision=_sim_version,
            )

        @app.callback(
            Output("currents-visible-store", "data"),
            Output("app-loading-signal", "children", allow_duplicate=True),
            Input("toggle-currents-btn", "n_clicks"),
            State("currents-visible-store", "data"),
            prevent_initial_call=True,
        )
        def toggle_currents_visibility(_, is_visible):
            return (not is_visible), f"currents-toggle:{int(not bool(is_visible))}"

        @app.callback(Output("toggle-currents-btn", "children"), Input("currents-visible-store", "data"))
        def update_currents_button(is_visible):
            return "Ocultar corrientes" if is_visible else "Mostrar corrientes"

        @app.callback(
            Output("transport-visible-store", "data"),
            Output("app-loading-signal", "children", allow_duplicate=True),
            Input("toggle-transport-btn", "n_clicks"),
            State("transport-visible-store", "data"),
            prevent_initial_call=True,
        )
        def toggle_transport_visibility(_, is_visible):
            return (not is_visible), f"transport-toggle:{int(not bool(is_visible))}"

        @app.callback(Output("toggle-transport-btn", "children"), Input("transport-visible-store", "data"))
        def update_transport_button(is_visible):
            return "Ocultar transporte previsto" if is_visible else "Mostrar transporte previsto"

        @app.callback(
            Output("current-layer-container", "children"),
            Input("currents-visible-store", "data"),
            Input("sim-version-store", "data"),
        )
        def render_current_layers(is_visible, sim_version):
            service = get_service()
            current_speed_min, current_speed_max = service.current_speed_range
            return build_current_layer_group(
                is_visible,
                sim_version,
                service.get_environment_month(),
                service.grid_features,
                service.get_current_for_cell,
                current_speed_min,
                current_speed_max,
            )

        @app.callback(
            Output("summary-body", "children"),
            Output("summary-body", "style"),
            Output("summary-panel", "style"),
            Input("sim-version-store", "data"),
        )
        def update_summary_body(_sim_version):
            service = get_service()
            summary_rows = build_summary_panel(service.get_summary())
            return (
                summary_rows,
                sidebar_summary_body_style(summary_rows),
                sidebar_summary_panel_style(summary_rows),
            )

        @app.callback(
            Output("detail-body", "children"),
            Output("detail-body", "style"),
            Output("sidebar-fit-area", "style"),
            Input("selected-cell-store", "data"),
            Input("sim-version-store", "data"),
        )
        def update_detail_body(selected_cell_id, _sim_version):
            service = get_service()
            detail_content = build_detail_panel(
                selected_cell_id,
                service.cells_by_id,
                self.build_current_detail,
                self.cell_state_label,
            )
            return (
                detail_content,
                sidebar_detail_panel_style(detail_content),
                sidebar_fit_area_style(detail_content, None),
            )

        @app.callback(
            Output("sidebar-active-panel-store", "data"),
            Input("sidebar-summary-tab", "n_clicks"),
            Input("sidebar-detail-tab", "n_clicks"),
            State("sidebar-active-panel-store", "data"),
            prevent_initial_call=True,
        )
        def update_sidebar_active_panel(_summary_clicks, _detail_clicks, active_panel):
            trigger = ctx.triggered_id
            if trigger == "sidebar-detail-tab":
                return SIDEBAR_PANEL_DETAIL
            if trigger == "sidebar-summary-tab":
                return SIDEBAR_PANEL_SUMMARY
            return active_panel or SIDEBAR_PANEL_SUMMARY

        @app.callback(
            Output("sidebar-summary-tab", "style"),
            Output("sidebar-detail-tab", "style"),
            Output("summary-panel-container", "style"),
            Output("detail-panel-container", "style"),
            Input("sidebar-active-panel-store", "data"),
        )
        def update_sidebar_panel_visibility(active_panel):
            active_panel = active_panel or SIDEBAR_PANEL_SUMMARY
            summary_is_active = active_panel == SIDEBAR_PANEL_SUMMARY
            detail_is_active = active_panel == SIDEBAR_PANEL_DETAIL
            return (
                sidebar_tab_button_style(summary_is_active),
                sidebar_tab_button_style(detail_is_active),
                sidebar_panel_container_style(summary_is_active),
                sidebar_panel_container_style(detail_is_active),
            )

        @app.callback(
            Output("real-month-badge", "children"),
            Output("real-month-badge", "style"),
            Output("simulation-progress", "children"),
            Input("sim-version-store", "data"),
            Input("currents-visible-store", "data"),
        )
        def update_time_indicators(_sim_version, _currents_visible):
            service = get_service()
            real_month_label = self.get_real_month_label()
            progress_percent = self.get_progress_percent()
            progress_target_month = self.get_progress_target_month()
            return (
                build_real_month_badge_children(real_month_label),
                real_month_badge_style(False),
                build_simulation_progress_children(
                    real_month_label,
                    service.current_month,
                    progress_target_month,
                    progress_percent,
                ),
            )

        @app.callback(
            Output("simulation-download", "data"),
            Input("save-simulation-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def save_simulation(_save_clicks):
            service = get_service()
            current_month = service.current_month
            filename = f"simulacion_mes_{current_month}.csv"
            csv_content = self.csv_serializer.export(service)
            return dcc.send_string(csv_content, filename)

        @app.callback(Output("selection-layer", "children"), Input("selected-cell-store", "data"))
        def render_selection_layer(selected_cell_id):
            service = get_service()
            return build_selection_layer(selected_cell_id, service.features_by_id)

        @app.callback(
            Output("selected-cell-store", "data", allow_duplicate=True),
            Output("seed-cell-adults", "value", allow_duplicate=True),
            Output("seed-cell-juveniles", "value", allow_duplicate=True),
            Output("seed-cell-larvae", "value", allow_duplicate=True),
            Output("seed-input-source-store", "data", allow_duplicate=True),
            Output({"type": "grid-geojson", "state": ALL}, "clickData", allow_duplicate=True),
            Output("seed-draft-geojson", "clickData", allow_duplicate=True),
            Output("colonizable-boundary-geojson", "clickData", allow_duplicate=True),
            Input({"type": "grid-geojson", "state": ALL}, "clickData"),
            Input("seed-draft-geojson", "clickData"),
            Input("colonizable-boundary-geojson", "clickData"),
            State("seed-draft-store", "data"),
            prevent_initial_call=True,
        )
        def select_cell_by_click(_grid_clicks, _seed_draft_click, _boundary_click, seed_draft):
            service = get_service()
            cleared_grid_clicks = [None] * len(_grid_clicks or [])
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update, no_update, cleared_grid_clicks, None, None
            click_data = ctx.triggered[0].get("value")
            properties = (click_data or {}).get("properties") or {}
            cell_id = properties.get("cell_id") or properties.get("id")
            if cell_id in service.cells_by_id:
                adults, juveniles, larvae = get_seed_cell_values(cell_id, seed_draft)
                return cell_id, adults, juveniles, larvae, cell_id, cleared_grid_clicks, None, None
            return no_update, no_update, no_update, no_update, no_update, cleared_grid_clicks, None, None

        app.clientside_callback(
            """
            function(_keyboardEvents, currentCell, keyboardEvent, gridNavigation) {
                const key = (keyboardEvent || {}).key;
                const navigation = gridNavigation || {};
                const rows = navigation.rows || 0;
                const cols = navigation.cols || 0;
                if (!currentCell || !key || rows <= 0 || cols <= 0) {
                    return currentCell;
                }

                if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(key)) {
                    return currentCell;
                }

                const match = /^([A-Z]+)(\\d+)$/.exec(currentCell);
                if (!match) {
                    return currentCell;
                }

                const rowLetters = match[1];
                let row = rowLetters.charCodeAt(0) - 65;
                let col = parseInt(match[2], 10) - 1;

                if (Number.isNaN(row) || Number.isNaN(col)) {
                    return currentCell;
                }

                if (key === "ArrowUp") {
                    row = Math.max(0, row - 1);
                } else if (key === "ArrowDown") {
                    row = Math.min(rows - 1, row + 1);
                } else if (key === "ArrowLeft") {
                    col = Math.max(0, col - 1);
                } else if (key === "ArrowRight") {
                    col = Math.min(cols - 1, col + 1);
                }

                return `${String.fromCharCode(65 + row)}${col + 1}`;
            }
            """,
            Output("selected-cell-store", "data", allow_duplicate=True),
            Input("keyboard-listener", "n_events"),
            State("selected-cell-store", "data"),
            State("keyboard-listener", "event"),
            State("grid-navigation-store", "data"),
            prevent_initial_call=True,
        )

        @app.callback(
            Output("map", "viewport"),
            Input("focus-grid-btn", "n_clicks"),
            Input("focus-coast-btn", "n_clicks"),
            prevent_initial_call=True,
        )
        def update_map_view(grid_clicks, coast_clicks):
            service = get_service()
            trigger = ctx.triggered_id
            if trigger == "focus-coast-btn":
                return {
                    "center": [
                        service.grid.south + ((service.grid.north - service.grid.south) * 0.68),
                        service.grid.west + ((service.grid.east - service.grid.west) * 0.33),
                    ],
                    "zoom": 6.8,
                    "transition": "setView",
                }
            return {
                "center": [
                    (service.grid.south + service.grid.north) / 2,
                    service.grid.west + ((service.grid.east - service.grid.west) * 0.33),
                ],
                "zoom": 7.8,
                "transition": "setView",
            }

        @app.callback(
            Output("sidebar-visible-store", "data"),
            Input("close-sidebar-btn", "n_clicks"),
            Input("open-sidebar-btn", "n_clicks"),
            State("sidebar-visible-store", "data"),
            prevent_initial_call=True,
        )
        def toggle_sidebar_visibility(_close_clicks, _open_clicks, is_visible):
            trigger = ctx.triggered_id
            if trigger == "close-sidebar-btn":
                return False
            if trigger == "open-sidebar-btn":
                return True
            return is_visible

        @app.callback(
            Output("sidebar-container", "style"),
            Output("open-sidebar-container", "style"),
            Input("sidebar-visible-store", "data"),
            Input("seed-active-store", "data"),
        )
        def render_sidebar(is_visible, seed_active):
            is_visible = bool(is_visible) and not bool(seed_active)
            open_button_style = {"display": "none" if is_visible or seed_active else "block"}
            return sidebar_style(is_visible), open_button_style
