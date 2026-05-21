import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.utils.parsing import parse_non_negative_int

if TYPE_CHECKING:
    from src.domain.entities import Grid


@dataclass(frozen=True)
class SimulationParameters:
    female_ratio: float = 0.46
    larval_mortality: float = 0.9999085758
    juvenile_mortality: float = 0.165
    adult_mortality: float = 0.052
    colonizable_max_depth_m: int = 300
    saturation_threshold: int = 1_000
    juvenile_mortality_multiplier: float = 3.5
    adult_mortality_multiplier: float = 3.0
    larvae_per_female_month: int = 200_000
    juvenile_months: int = 11
    larval_days: int = 30
    cell_size_m: int = 10_000
    seconds_per_day: int = 86_400
    max_transport_steps: int = 500
    max_simulation_month: int = 36
    current_weight: float = 0.90
    temperature_weight: float = 0.02
    depth_weight: float = 0.02
    salinity_weight: float = 0.02
    parameter_penalty: float = 0.01
    min_temperature_c: int = 10
    min_salinity: float = 34.11
    max_salinity: float = 38.11
    moore_deltas: tuple[tuple[int, int], ...] = (
        (0, 1),
        (-1, 1),
        (-1, 0),
        (-1, -1),
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
    )

    @property
    def outside_grid_score(self) -> float:
        return self.temperature_weight + self.salinity_weight + self.parameter_penalty


@dataclass(frozen=True)
class DensityMortalityConfig:
    saturation_threshold: int
    juvenile_mortality_multiplier: float
    adult_mortality_multiplier: float

    def as_dict(self) -> dict[str, int | float]:
        return {
            "saturation_threshold": self.saturation_threshold,
            "juvenile_mortality_multiplier": self.juvenile_mortality_multiplier,
            "adult_mortality_multiplier": self.adult_mortality_multiplier,
        }


@dataclass(frozen=True)
class SeedRules:
    max_lionfish_grid: int = 10_000_000
    max_lionfish_per_cell: int = 500_000
    min_larvae_per_cell: int = 200_000
    max_transport_larvae_per_cell: int = 50_000_000
    initial_fish_empty_probability: float = 0.90
    initial_fish_min_units: int = 1
    initial_fish_max_units: int = 1_000
    initial_larvae_empty_probability: float = 0.98
    initial_larvae_min_units: int = 200_000
    initial_larvae_max_units: int = 50_000_000


@dataclass(frozen=True)
class SeedDefinition:
    cells_by_id: dict[str, dict[str, int]]

    @classmethod
    def from_mapping(cls, seed_by_cell: dict[str, dict[str, int]] | None) -> "SeedDefinition":
        return cls(
            {
                cell_id: {
                    "adults": int((values or {}).get("adults", 0) or 0),
                    "juveniles": int((values or {}).get("juveniles", 0) or 0),
                    "larvae": int((values or {}).get("larvae", 0) or 0),
                }
                for cell_id, values in (seed_by_cell or {}).items()
            }
        )

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {
            cell_id: dict(values)
            for cell_id, values in self.cells_by_id.items()
        }

    def merge_missing(self, other: "SeedDefinition") -> "SeedDefinition":
        merged = self.as_dict()
        for cell_id, values in other.cells_by_id.items():
            merged.setdefault(cell_id, dict(values))
        return SeedDefinition(merged)

    @staticmethod
    def split_fish_by_random_proportion(total_units: int, seed_random: random.Random) -> tuple[int, int]:
        juvenile_step = seed_random.randint(0, 10)
        juveniles = (total_units * juvenile_step + 5) // 10
        adults = total_units - juveniles
        return adults, juveniles

    @classmethod
    def build_probabilistic(
        cls,
        grid: "Grid",
        seed_rules,
        seed_random: random.Random,
        excluded_cell_ids: set[str] | None = None,
    ) -> "SeedDefinition":
        excluded_cell_ids = set(excluded_cell_ids or ())
        seed = {}

        for cell in grid.colonizable_cells:
            if cell.cell_id in excluded_cell_ids or seed_random.random() < seed_rules.initial_fish_empty_probability:
                continue

            total_units = seed_random.randint(
                seed_rules.initial_fish_min_units,
                seed_rules.initial_fish_max_units,
            )
            adults, juveniles = cls.split_fish_by_random_proportion(total_units, seed_random)
            seed.setdefault(cell.cell_id, {"adults": 0, "juveniles": 0, "larvae": 0})
            seed[cell.cell_id]["adults"] = adults
            seed[cell.cell_id]["juveniles"] = juveniles

        for cell in grid.transport_cells:
            if cell.cell_id in excluded_cell_ids or seed_random.random() < seed_rules.initial_larvae_empty_probability:
                continue

            larvae_units = seed_random.randint(
                seed_rules.initial_larvae_min_units,
                seed_rules.initial_larvae_max_units,
            )
            seed.setdefault(cell.cell_id, {"adults": 0, "juveniles": 0, "larvae": 0})
            seed[cell.cell_id]["larvae"] = larvae_units

        return cls.from_mapping(seed)

    @classmethod
    def build_assisted(
        cls,
        seed_by_cell: dict[str, dict[str, int]] | None,
        grid: "Grid",
        seed_rules,
        seed_random: random.Random,
    ) -> "SeedDefinition":
        manual_seed = cls.from_mapping(seed_by_cell)
        probabilistic_seed = cls.build_probabilistic(
            grid,
            seed_rules,
            seed_random,
            excluded_cell_ids=set(manual_seed.cells_by_id),
        )
        return manual_seed.merge_missing(probabilistic_seed)


class SeedValidator:
    def __init__(self, grid: "Grid", seed_rules: SeedRules) -> None:
        self.grid = grid
        self.seed_rules = seed_rules

    def validate_cell(
        self,
        cell_id: str,
        adults: int,
        juveniles: int,
        larvae: int,
    ) -> str | None:
        cell = self.grid.get_cell(cell_id)
        if cell is None:
            return "Selecciona una celda valida."
        if min(adults, juveniles, larvae) < 0:
            return "No uses valores negativos."
        if adults + juveniles > self.seed_rules.max_lionfish_per_cell:
            return f"Maximo por celda: {self.seed_rules.max_lionfish_per_cell} adultos + juveniles."
        if adults + juveniles > 0 and not cell.can_be_colonized():
            return "Esa celda no puede iniciar colonizada."
        if larvae > 0 and not cell.allows_transport():
            return "Esa celda no permite transporte larval."
        if larvae > self.seed_rules.max_transport_larvae_per_cell:
            return f"Maximo de larvas por celda: {self.seed_rules.max_transport_larvae_per_cell}."
        if larvae and larvae < self.seed_rules.min_larvae_per_cell:
            return f"Minimo de larvas por celda: {self.seed_rules.min_larvae_per_cell}."
        if adults + juveniles == 0 and larvae == 0:
            return "La celda no tiene unidades para guardar."
        return None

    def validate_grid(
        self,
        seed_by_cell: dict[str, dict] | None,
        require_cells: bool = True,
    ) -> str | None:
        seed_by_cell = seed_by_cell or {}
        if require_cells and not seed_by_cell:
            return "La semilla no tiene celdas guardadas."

        adults_total = 0
        juveniles_total = 0
        errors = []

        for cell_id, values in seed_by_cell.items():
            adults = parse_non_negative_int(values.get("adults", 0))
            juveniles = parse_non_negative_int(values.get("juveniles", 0))
            larvae = parse_non_negative_int(values.get("larvae", 0))

            if None in (adults, juveniles, larvae):
                errors.append(f"{cell_id}: Revisa las cantidades.")
                continue

            adults_total += adults
            juveniles_total += juveniles

            cell_error = self.validate_cell(cell_id, adults, juveniles, larvae)
            if cell_error:
                errors.append(f"{cell_id}: {cell_error}")

        if adults_total + juveniles_total > self.seed_rules.max_lionfish_grid:
            errors.append(f"Maximo total: {self.seed_rules.max_lionfish_grid} adultos + juveniles.")

        return " · ".join(errors) if errors else None
