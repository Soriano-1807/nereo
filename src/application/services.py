import random

from src.domain.entities import Cell, TransportEvent, Grid
from src.domain.sim_config import DensityMortalityConfig, SeedDefinition, SeedRules, SeedValidator, SimulationParameters
from src.domain.simulation import Simulator
from src.infrastructure.environment_data import EnvironmentRepository
from src.utils.parsing import parse_min_float, parse_non_negative_int, parse_positive_int


class SimulationService:
    def __init__(
        self,
        lon_lines: list[float],
        lat_lines: list[float],
        repository: EnvironmentRepository | None = None,
        simulator_cls=Simulator,
        seed_rules: SeedRules | None = None,
        seed_random: random.Random | None = None,
        simulation_parameters: SimulationParameters | None = None,
    ) -> None:
        self.lon_lines = lon_lines
        self.lat_lines = lat_lines
        repository = repository or EnvironmentRepository()
        self.environment = repository.load_all()
        self.simulation_parameters = simulation_parameters or SimulationParameters()
        self.grid = Grid.create(
            lon_lines=lon_lines,
            lat_lines=lat_lines,
            environment_dataset=self.environment,
            colonizable_max_depth_m=self.simulation_parameters.colonizable_max_depth_m,
        )
        self.grid_features = self.grid.features
        self.simulator = simulator_cls(
            self.grid,
            self.environment.currents,
            self.environment.months,
            self.environment.environment,
            parameters=self.simulation_parameters,
        )
        self.seed_rules = seed_rules or SeedRules()
        self.seed_random = seed_random or random.Random()

    @property
    def cells_by_id(self) -> dict[str, Cell]:
        return self.grid.cells_by_id

    @property
    def features_by_id(self) -> dict[str, dict]:
        return self.grid.features_by_id

    @property
    def colonizable_feature_ids(self) -> set[str]:
        return self.grid.colonizable_feature_ids

    @property
    def current_speed_range(self) -> tuple[float | None, float | None]:
        return self.environment.current_speed_range()

    @property
    def temperature_range(self) -> tuple[float | None, float | None]:
        return self.environment.temperature_range()

    @property
    def salinity_range(self) -> tuple[float | None, float | None]:
        return self.environment.salinity_range()

    @property
    def juvenile_mortality_rate(self) -> float:
        return self.simulation_parameters.juvenile_mortality

    @property
    def adult_mortality_rate(self) -> float:
        return self.simulation_parameters.adult_mortality

    @property
    def current_month(self) -> int:
        return self.simulator.current_month

    def get_environment_month(self) -> str | None:
        if not self.environment.months:
            return None
        return self.environment.months[self.current_month % len(self.environment.months)]

    def get_current_for_cell(self, cell_id: str, month: str | None) -> dict[str, float] | None:
        if month is None:
            return None
        return self.environment.currents.get((cell_id, month))

    def get_transport_events(self) -> list[TransportEvent]:
        return self.simulator.pending_transport

    def has_population(self) -> bool:
        return self.grid.has_population()

    def build_probabilistic_seed(self, excluded_cell_ids: set[str] | None = None) -> dict[str, dict[str, int]]:
        return SeedDefinition.build_probabilistic(
            self.grid,
            self.seed_rules,
            self.seed_random,
            excluded_cell_ids=excluded_cell_ids,
        ).as_dict()

    def build_assisted_seed(self, seed_by_cell: dict[str, dict[str, int]] | None) -> dict[str, dict[str, int]]:
        return SeedDefinition.build_assisted(
            seed_by_cell,
            self.grid,
            self.seed_rules,
            self.seed_random,
        ).as_dict()

    def reset_simulation(self) -> None:
        self.grid.reset()
        self.simulator.reset()

    def apply_seed(self, seed_by_cell: dict[str, dict[str, int]] | None) -> None:
        self.reset_simulation()
        seed_definition = SeedDefinition.from_mapping(seed_by_cell)

        for cell_id, seed_data in seed_definition.cells_by_id.items():
            if not (cell := self.grid.get_cell(cell_id)):
                continue

            for pop_type in ("adults", "juveniles", "larvae"):
                if count := seed_data.get(pop_type, 0):
                    self.simulator.seed_population(cell.row, cell.col, pop_type, count)

        self.simulator.plan_next_transport()

    def step(self) -> bool:
        return self.simulator.step()

    def can_advance_simulation(self) -> bool:
        return self.current_month < self.simulation_parameters.max_simulation_month

    def get_summary(self) -> dict:
        return self.simulator.get_summary()

    def default_density_config(self) -> DensityMortalityConfig:
        return DensityMortalityConfig(
            self.simulation_parameters.saturation_threshold,
            self.simulation_parameters.juvenile_mortality_multiplier,
            self.simulation_parameters.adult_mortality_multiplier,
        )

    def apply_density_config(self, density_config: DensityMortalityConfig | None) -> None:
        self.simulator.set_density_mortality_config(density_config or self.default_density_config())

    def parse_seed_input_for_match(self, value: object) -> int | None:
        if not value or (isinstance(value, str) and not value.strip()):
            return None
        return parse_non_negative_int(value)

    def validate_seed(self, seed_by_cell: dict | None) -> str | None:
        validator = SeedValidator(self.grid, self.seed_rules)
        return validator.validate_grid(seed_by_cell, require_cells=True)

    def validate_density_controls(
        self,
        saturation_threshold: object,
        juvenile_multiplier: object,
        adult_multiplier: object,
    ) -> tuple[DensityMortalityConfig | None, str | None]:
        threshold = parse_positive_int(saturation_threshold)
        if threshold is None:
            return None, "El umbral de saturacion debe ser un entero mayor a 0."

        juvenile_multiplier = parse_min_float(juvenile_multiplier, 1.0)
        if juvenile_multiplier is None:
            return None, "El multiplicador de mortalidad juvenil debe ser mayor o igual a 1."

        adult_multiplier = parse_min_float(adult_multiplier, 1.0)
        if adult_multiplier is None:
            return None, "El multiplicador de mortalidad adulta debe ser mayor o igual a 1."

        return DensityMortalityConfig(
            saturation_threshold=threshold,
            juvenile_mortality_multiplier=juvenile_multiplier,
            adult_mortality_multiplier=adult_multiplier,
        ), None
