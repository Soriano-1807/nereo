import random

from src.domain.sim_config import DensityMortalityConfig, SimulationParameters
from src.domain.entities import Cell, Grid, TransportEvent, split_by_sex, survivors


class LarvalTransportRouter:
    def __init__(
        self,
        grid: Grid,
        current_by_cell_month: dict[tuple[str, str], dict[str, float]] | None = None,
        environment_by_cell_month: dict[tuple[str, str], dict[str, float]] | None = None,
        parameters: SimulationParameters | None = None,
    ) -> None:
        self.grid = grid
        self.current_by_cell_month = current_by_cell_month or {}
        self.environment_by_cell_month = environment_by_cell_month or {}
        self.parameters = parameters or SimulationParameters()

    def plan_next_transport(self, current_month: int, environment_month: str | None = None) -> list[TransportEvent]:
        planned_transport: list[TransportEvent] = []

        for cell in self.grid.iter_cells():
            total_larvae = cell.total_larvae()
            if total_larvae <= 0:
                continue

            target, path = self.trace_larval_transport(cell, environment_month)
            if target is None:
                planned_transport.append(
                    TransportEvent(
                        month=current_month,
                        environment_month=environment_month,
                        source_cell_id=cell.cell_id,
                        destination_cell_id="Fuera de grilla",
                        path=path,
                        larvae_units=total_larvae,
                        dead_larvae=total_larvae,
                        incoming_larvae=None,
                        target_position=None,
                    )
                )
                continue

            alive_larvae = survivors(total_larvae, self.parameters.larval_mortality)
            incoming_larvae = split_by_sex(alive_larvae, self.parameters.female_ratio)
            planned_transport.append(
                TransportEvent(
                    month=current_month,
                    environment_month=environment_month,
                    source_cell_id=cell.cell_id,
                    destination_cell_id=target.cell_id,
                    path=path,
                    larvae_units=total_larvae,
                    dead_larvae=total_larvae - alive_larvae,
                    incoming_larvae=incoming_larvae,
                    target_position=(target.row, target.col),
                )
            )

        return planned_transport

    def apply_planned_transport(self, planned_transport: list[TransportEvent]) -> tuple[dict[tuple[int, int], dict[str, int]], int]:
        incoming_larvae: dict[tuple[int, int], dict[str, int]] = {}
        dead_larvae = 0

        for event in planned_transport:
            dead_larvae += event.dead_larvae
            if event.target_position is None or event.incoming_larvae is None:
                continue

            incoming_larvae.setdefault(event.target_position, {"F": 0, "M": 0})
            for sex, count in event.incoming_larvae.items():
                incoming_larvae[event.target_position][sex] += count

        return incoming_larvae, dead_larvae

    def trace_larval_transport(self, start_cell: Cell, environment_month: str | None) -> tuple[Cell | None, list[str]]:
        current_cell = start_cell
        days_left = self.parameters.larval_days
        path = [start_cell.cell_id]
        steps = 0

        while days_left > 0 and steps < self.parameters.max_transport_steps:
            current = self.get_current_for_cell(current_cell, environment_month)
            if current is None:
                break

            travel_days = self.crossing_days(current["speed"])
            if travel_days > days_left:
                break

            target_row, target_col = self.choose_transport_neighbor(current_cell, current, environment_month)
            if not (0 <= target_row < self.grid.rows and 0 <= target_col < self.grid.cols):
                return None, path

            target_cell = self.grid.get_cell(target_row, target_col)
            if target_cell is None:
                return None, path
            if target_cell.prohibited or target_cell.cell_id == current_cell.cell_id:
                break

            current_cell = target_cell
            path.append(current_cell.cell_id)
            days_left -= travel_days
            steps += 1

        return current_cell, path

    def choose_transport_neighbor(self, cell: Cell, current: dict[str, float] | None, environment_month: str | None) -> tuple[int, int]:
        if cell.prohibited or current is None:
            return cell.row, cell.col

        candidates = self.score_moore_neighbors(cell, current, environment_month)
        total_score = sum(candidate["score"] for candidate in candidates)
        if total_score <= 0:
            return self.get_current_target_position(cell, current)

        draw = random.random()
        cumulative = 0.0
        for candidate in candidates:
            cumulative += candidate["score"] / total_score
            if draw <= cumulative:
                return candidate["row"], candidate["col"]

        last_candidate = candidates[-1]
        return last_candidate["row"], last_candidate["col"]

    def score_moore_neighbors(self, cell: Cell, current: dict[str, float], environment_month: str | None) -> list[dict[str, float | int]]:
        down_current_sector = self.direction_to_sector(current["direction_degrees"])
        candidates = []

        for sector, (row_delta, col_delta) in enumerate(self.parameters.moore_deltas):
            row = cell.row + row_delta
            col = cell.col + col_delta
            score = 0.0

            if sector == down_current_sector:
                score += self.parameters.current_weight

            neighbor = self.grid.get_cell(row, col)
            score += self.static_suitability_score(neighbor, environment_month)
            candidates.append({"row": row, "col": col, "score": score})

        return candidates

    def static_suitability_score(self, cell: Cell | None, environment_month: str | None) -> float:
        if cell is None:
            return self.parameters.outside_grid_score

        environment = self.environment_by_cell_month.get((cell.cell_id, environment_month), {})
        score = 0.0

        temperature = environment.get("temperature")
        if temperature is not None and temperature > self.parameters.min_temperature_c:
            score += self.parameters.temperature_weight

        salinity = environment.get("salinity")
        if salinity is not None and self.parameters.min_salinity <= salinity <= self.parameters.max_salinity:
            score += self.parameters.salinity_weight

        depth = environment.get("depth", cell.depth_m)
        if depth is not None and depth <= self.parameters.colonizable_max_depth_m:
            score += self.parameters.depth_weight

        return score or self.parameters.parameter_penalty

    def get_current_for_cell(self, cell: Cell, environment_month: str | None) -> dict[str, float] | None:
        return self.current_by_cell_month.get((cell.cell_id, environment_month))

    def crossing_days(self, speed: float) -> float:
        if speed <= 0:
            return self.parameters.larval_days
        return (self.parameters.cell_size_m / speed) / self.parameters.seconds_per_day

    def direction_to_delta(self, direction_degrees: float) -> tuple[int, int]:
        sector = int((direction_degrees % 360) // 45)
        return self.parameters.moore_deltas[sector]

    def direction_to_sector(self, direction_degrees: float) -> int:
        return int((direction_degrees % 360) // 45)

    def get_current_target_position(self, cell: Cell, current: dict[str, float] | None) -> tuple[int, int]:
        if cell.prohibited or current is None:
            return cell.row, cell.col

        row_delta, col_delta = self.direction_to_delta(current["direction_degrees"])
        return cell.row + row_delta, cell.col + col_delta


class Simulator:
    def __init__(
        self,
        grid: Grid,
        current_by_cell_month: dict[tuple[str, str], dict[str, float]] | None = None,
        environment_months: list[str] | None = None,
        environment_by_cell_month: dict[tuple[str, str], dict[str, float]] | None = None,
        parameters: SimulationParameters | None = None,
    ) -> None:
        self.grid = grid
        self.parameters = parameters or SimulationParameters()
        self.environment_months = environment_months or []
        self.router = LarvalTransportRouter(
            grid=grid,
            current_by_cell_month=current_by_cell_month,
            environment_by_cell_month=environment_by_cell_month,
            parameters=self.parameters,
        )
        self.current_month = 0
        self.pending_transport: list[TransportEvent] = []
        self.pending_transport_month: str | None = None
        self.dead_larvae_count = 0
        self.dead_lionfish_count = 0
        self.density_mortality_config = DensityMortalityConfig(
            saturation_threshold=self.parameters.saturation_threshold,
            juvenile_mortality_multiplier=self.parameters.juvenile_mortality_multiplier,
            adult_mortality_multiplier=self.parameters.adult_mortality_multiplier,
        )

    def can_advance(self) -> bool:
        return self.current_month < self.parameters.max_simulation_month

    def set_density_mortality_config(self, density_mortality_config: DensityMortalityConfig) -> None:
        self.density_mortality_config = density_mortality_config

    def reset(self) -> None:
        self.current_month = 0
        self.pending_transport = []
        self.pending_transport_month = None
        self.dead_larvae_count = 0
        self.dead_lionfish_count = 0
        self.plan_next_transport()

    def get_density_adjusted_mortality_rates(self, cell: Cell) -> tuple[float, float]:
        juvenile_mortality = self.parameters.juvenile_mortality
        adult_mortality = self.parameters.adult_mortality

        if cell.total_lionfish() >= self.density_mortality_config.saturation_threshold:
            juvenile_mortality *= self.density_mortality_config.juvenile_mortality_multiplier
            adult_mortality *= self.density_mortality_config.adult_mortality_multiplier

        return min(1.0, juvenile_mortality), min(1.0, adult_mortality)

    def seed_population(self, row: int, col: int, population_type: str, count: int) -> None:
        cell = self.grid.get_cell(row, col)
        if cell is None:
            return

        if population_type == "larvae" and not cell.allows_transport():
            return
        if population_type in ("juveniles", "adults") and not cell.can_be_colonized():
            return

        for sex, sex_count in split_by_sex(count, self.parameters.female_ratio).items():
            if population_type == "larvae":
                cell.add_larvae(sex, sex_count)
            elif population_type == "juveniles":
                cell.add_juvenile(sex, 0, sex_count)
            elif population_type == "adults":
                cell.add_adult(sex, 0, sex_count)

    def step(self) -> bool:
        if not self.can_advance():
            return False

        environment_month = self.get_environment_month()
        if self.pending_transport_month != environment_month:
            self.plan_next_transport(environment_month)

        incoming_larvae, dead_larvae = self.router.apply_planned_transport(self.pending_transport)
        dead_lionfish = self.age_and_survive_lionfish()

        self.clear_all_larvae()
        settlement_deaths = self.place_larvae_as_juveniles(incoming_larvae)
        self.current_month += 1
        self.spawn_larvae()
        self.plan_next_transport()

        self.dead_larvae_count += dead_larvae
        self.dead_lionfish_count += dead_lionfish + settlement_deaths
        return True

    def spawn_larvae(self) -> None:
        for cell in self.grid.iter_cells():
            births = cell.adult_females() * self.parameters.larvae_per_female_month
            if births <= 0:
                continue

            for sex, count in split_by_sex(births, self.parameters.female_ratio).items():
                cell.add_larvae(sex, count)

    def plan_next_transport(self, environment_month: str | None = None) -> list[TransportEvent]:
        environment_month = environment_month or self.get_environment_month()
        self.pending_transport = self.router.plan_next_transport(self.current_month, environment_month)
        self.pending_transport_month = environment_month
        return self.pending_transport

    def age_and_survive_lionfish(self) -> int:
        dead_lionfish = 0

        for cell in self.grid.iter_cells():
            juvenile_mortality, adult_mortality = self.get_density_adjusted_mortality_rates(cell)
            dead_lionfish += cell.advance_one_month(
                juvenile_mortality=juvenile_mortality,
                adult_mortality=adult_mortality,
                juvenile_months=self.parameters.juvenile_months,
                female_ratio=self.parameters.female_ratio,
            )

        return dead_lionfish

    def place_larvae_as_juveniles(self, incoming_larvae: dict[tuple[int, int], dict[str, int]]) -> int:
        dead_settlement = 0

        for (row, col), larvae_by_sex in incoming_larvae.items():
            target = self.grid.get_cell(row, col)
            if target is None or not target.can_be_colonized():
                dead_settlement += sum(larvae_by_sex.values())
                continue

            for sex, count in larvae_by_sex.items():
                target.add_juvenile(sex, 0, count)

        return dead_settlement

    def clear_all_larvae(self) -> None:
        for cell in self.grid.iter_cells():
            cell.clear_larvae()

    def get_environment_month(self) -> str | None:
        if not self.environment_months:
            return None
        return self.environment_months[self.current_month % len(self.environment_months)]

    def get_summary(self) -> dict:
        colonized = 0
        larvae_cells = 0
        empty = 0
        lionfish_units = 0
        larvae_units = 0
        juvenile_units = 0
        adult_females = 0

        for cell in self.grid.iter_cells():
            state = cell.visible_state()
            total_larvae = cell.total_larvae()
            lionfish_units += cell.total_lionfish()
            larvae_units += total_larvae
            juvenile_units += cell.total_juveniles()
            adult_females += cell.adult_females()
            if state == "colonizada":
                colonized += 1
            elif state != "transporte":
                empty += 1

            if total_larvae > 0:
                larvae_cells += 1

        destination_cells = {
            event.destination_cell_id
            for event in self.pending_transport
            if event.target_position is not None
        }
        routes_outside_grid = sum(1 for event in self.pending_transport if event.exits_grid)

        return {
            "month": self.current_month,
            "colonized": colonized,
            "larvae_cells": larvae_cells,
            "destination_cells": len(destination_cells),
            "routes_outside_grid": routes_outside_grid,
            "empty": empty,
            "lionfish_units": lionfish_units,
            "juvenile_units": juvenile_units,
            "adult_females": adult_females,
            "larvae_units": larvae_units,
            "dead_larvae": self.dead_larvae_count,
            "dead_lionfish": self.dead_lionfish_count,
        }
