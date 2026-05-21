import csv
from functools import cached_property
from pathlib import Path

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentDataset:
    depth_by_cell: dict[str, float]
    temperatures: list[float]
    salinities: list[float]
    depths: list[float]
    months: list[str]
    cell_ids: set[str]
    currents: dict[tuple[str, str], dict[str, float]]
    environment: dict[tuple[str, str], dict[str, float]]
    speeds: list[float]

    def temperature_range(self) -> tuple[float | None, float | None]:
        return (min(self.temperatures), max(self.temperatures)) if self.temperatures else (None, None)

    def salinity_range(self) -> tuple[float | None, float | None]:
        return (min(self.salinities), max(self.salinities)) if self.salinities else (None, None)

    def current_speed_range(self) -> tuple[float | None, float | None]:
        return (min(self.speeds), max(self.speeds)) if self.speeds else (None, None)


class EnvironmentRepository:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "Dataset_Ambiental_Estacional_Final.csv"

    def __init__(self, data_path: Path | str | None = None):
        self.data_path = Path(data_path) if data_path is not None else self.DEFAULT_DATA_PATH

    @staticmethod
    def parse_float(value: str):
        if value is None or value.strip() == "":
            return None
        return float(value)

    @cached_property
    def dataset(self) -> EnvironmentDataset:
        depth_by_cell = {}
        temperatures = []
        salinities = []
        depths = []
        months = set()
        cell_ids = set()
        currents = {}
        environment = {}
        speeds = []

        with self.data_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                cell_id = row["cell_id"].strip()
                year_month = row["month"].strip()

                if cell_id:
                    cell_ids.add(cell_id)
                if year_month:
                    months.add(year_month)

                temperature = self.parse_float(row["temperature_median"])
                salinity = self.parse_float(row["salinity_median"])
                depth = self.parse_float(row["seafloor_depth_mean"])
                speed = self.parse_float(row["current_speed_median"])
                direction = self.parse_float(row["current_direction_deg_median"])

                if cell_id and cell_id not in depth_by_cell and depth is not None:
                    depth_by_cell[cell_id] = depth

                if temperature is not None:
                    temperatures.append(temperature)
                if salinity is not None:
                    salinities.append(salinity)
                if depth is not None:
                    depths.append(depth)

                if cell_id and year_month and temperature is not None and salinity is not None and depth is not None:
                    environment[(cell_id, year_month)] = {
                        "temperature": temperature,
                        "salinity": salinity,
                        "depth": depth,
                    }

                if cell_id and year_month and speed is not None and direction is not None:
                    currents[(cell_id, year_month)] = {
                        "speed": speed,
                        "direction_degrees": direction,
                    }

                if speed is not None:
                    speeds.append(speed)

        return EnvironmentDataset(
            depth_by_cell=depth_by_cell,
            temperatures=temperatures,
            salinities=salinities,
            depths=depths,
            months=sorted(months, key=int),
            cell_ids=cell_ids,
            currents=currents,
            environment=environment,
            speeds=speeds,
        )

    def load_all(self) -> EnvironmentDataset:
        return self.dataset

    def get_data_by_cell(self, cell_id: str, month: str):
        return self.dataset.environment.get((cell_id, month))

    def get_current_by_cell(self, cell_id: str, month: str):
        return self.dataset.currents.get((cell_id, month))
