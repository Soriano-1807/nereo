from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field

def split_by_sex(total: int, female_ratio: float) -> dict[str, int]:
    females = round(total * female_ratio)
    return {"F": females, "M": total - females}


def survivors(count: int, mortality_rate: float) -> int:
    mortality_rate = min(1.0, max(0.0, mortality_rate))
    return round(count * (1 - mortality_rate))


@dataclass
class Cell:
    cell_id: str
    row: int
    col: int
    depth_m: float
    colonizable_max_depth_m: float
    prohibited: bool = False
    larvae_by_sex: dict[str, int] = field(default_factory=lambda: {"F": 0, "M": 0})
    juveniles_by_sex_age: dict[tuple[str, int], int] = field(default_factory=lambda: defaultdict(int))
    adults_by_sex_age: dict[tuple[str, int], int] = field(default_factory=lambda: defaultdict(int))

    def allows_transport(self) -> bool:
        return not self.prohibited

    def can_be_colonized(self) -> bool:
        return (not self.prohibited) and self.depth_m < self.colonizable_max_depth_m

    def total_larvae(self) -> int:
        return sum(self.larvae_by_sex.values())

    def total_juveniles(self) -> int:
        return sum(self.juveniles_by_sex_age.values())

    def total_adults(self) -> int:
        return sum(self.adults_by_sex_age.values())

    def total_lionfish(self) -> int:
        return self.total_juveniles() + self.total_adults()

    @property
    def population(self) -> int:
        return self.total_lionfish() + self.total_larvae()

    @property
    def is_colonized(self) -> bool:
        return self.total_lionfish() > 0

    def adult_females(self) -> int:
        return sum(count for (sex, _), count in self.adults_by_sex_age.items() if sex == "F")

    def visible_state(self) -> str:
        if self.prohibited:
            return "prohibida"
        if self.total_lionfish() > 0:
            return "colonizada"
        return "transporte" if self.total_larvae() > 0 else "no_colonizada"

    def add_larvae(self, sex: str, count: int) -> None:
        if count > 0:
            self.larvae_by_sex[sex] += count

    def add_juvenile(self, sex: str, age: int, count: int) -> None:
        if count > 0:
            self.juveniles_by_sex_age[(sex, age)] += count

    def add_adult(self, sex: str, age: int, count: int) -> None:
        if count > 0:
            self.adults_by_sex_age[(sex, age)] += count

    def clear_larvae(self) -> None:
        self.larvae_by_sex = {"F": 0, "M": 0}

    def advance_one_month(
        self,
        juvenile_mortality: float,
        adult_mortality: float,
        juvenile_months: int,
        female_ratio: float,
    ) -> int:
        dead_lionfish = 0
        new_juveniles = defaultdict(int)
        adult_recruits = defaultdict(int)

        juvenile_totals_by_age = defaultdict(int)
        for (_sex, age), count in self.juveniles_by_sex_age.items():
            juvenile_totals_by_age[age] += count

        for age, count in juvenile_totals_by_age.items():
            alive = survivors(count, juvenile_mortality)
            dead_lionfish += count - alive
            next_age = age + 1

            bucket = adult_recruits if next_age >= juvenile_months else new_juveniles
            target_age = 0 if next_age >= juvenile_months else next_age
            for sex, sex_count in split_by_sex(alive, female_ratio).items():
                bucket[(sex, target_age)] += sex_count

        self.juveniles_by_sex_age = new_juveniles
        for (sex, age), count in adult_recruits.items():
            self.add_adult(sex, age, count)

        new_adults = defaultdict(int)
        adult_totals_by_age = defaultdict(int)
        for (_sex, age), count in self.adults_by_sex_age.items():
            adult_totals_by_age[age] += count

        for age, count in adult_totals_by_age.items():
            alive = survivors(count, adult_mortality)
            dead_lionfish += count - alive
            for sex, sex_count in split_by_sex(alive, female_ratio).items():
                new_adults[(sex, age + 1)] += sex_count

        self.adults_by_sex_age = new_adults
        return dead_lionfish

    def reset_population(self) -> None:
        self.clear_larvae()
        self.juveniles_by_sex_age.clear()
        self.adults_by_sex_age.clear()


@dataclass(frozen=True)
class TransportEvent:
    month: int
    environment_month: str | None
    source_cell_id: str
    destination_cell_id: str
    path: list[str]
    larvae_units: int
    dead_larvae: int
    incoming_larvae: dict[str, int] | None = None
    target_position: tuple[int, int] | None = None

    @property
    def exits_grid(self) -> bool:
        return self.destination_cell_id == "Fuera de grilla"

    def as_dict(self) -> dict:
        return {
            "month": self.month,
            "environment_month": self.environment_month,
            "from": self.source_cell_id,
            "to": self.destination_cell_id,
            "path": self.path,
            "larvae_units": self.larvae_units,
            "incoming_larvae": self.incoming_larvae,
            "dead_larvae": self.dead_larvae,
            "target_position": self.target_position,
        }


@dataclass
class Grid:
    lon_lines: list[float]
    lat_lines: list[float]
    features: list[dict]
    depth_by_cell: dict[str, float]
    available_cell_ids: set[str]
    colonizable_max_depth_m: float
    prohibited_cells: set[str] = field(init=False)
    cells_by_id: dict[str, Cell] = field(init=False)
    _matrix: list[list[Cell]] = field(init=False, repr=False)
    features_by_id: dict[str, dict] = field(init=False)
    features_by_position: dict[tuple[int, int], dict] = field(init=False)
    colonizable_feature_ids: set[str] = field(init=False)

    @staticmethod
    def validate_longitudes(lon_lines):
        if lon_lines is None or len(lon_lines) < 2:
            raise ValueError("La grilla requiere al menos dos longitudes.")
        if len(set(lon_lines)) != len(lon_lines):
            raise ValueError("Las longitudes no pueden repetirse.")

    @staticmethod
    def validate_latitudes(lat_lines):
        if lat_lines is None or len(lat_lines) < 2:
            raise ValueError("La grilla requiere al menos dos latitudes.")
        if len(set(lat_lines)) != len(lat_lines):
            raise ValueError("Las latitudes no pueden repetirse.")

    @classmethod
    def create_features(cls, lon_lines, lat_lines):
        cls.validate_longitudes(lon_lines)
        cls.validate_latitudes(lat_lines)

        features = []
        sorted_lons = sorted(lon_lines)
        sorted_lats = sorted(lat_lines, reverse=True)

        for row in range(len(sorted_lats) - 1):
            for col in range(len(sorted_lons) - 1):
                west = sorted_lons[col]
                east = sorted_lons[col + 1]
                north = sorted_lats[row]
                south = sorted_lats[row + 1]
                row_letter = chr(ord("A") + row)
                cell_id = f"{row_letter}{col + 1}"

                features.append(
                    {
                        "id": cell_id,
                        "row": row,
                        "col": col,
                        "positions": [
                            [south, west],
                            [south, east],
                            [north, east],
                            [north, west],
                            [south, west],
                        ],
                        "center": [(south + north) / 2, (west + east) / 2],
                    }
                )

        return features

    @classmethod
    def create(cls, lon_lines, lat_lines, environment_dataset, colonizable_max_depth_m):
        return cls(
            lon_lines=list(lon_lines),
            lat_lines=list(lat_lines),
            features=cls.create_features(lon_lines, lat_lines),
            depth_by_cell=environment_dataset.depth_by_cell,
            available_cell_ids=environment_dataset.cell_ids,
            colonizable_max_depth_m=colonizable_max_depth_m,
        )

    def __post_init__(self):
        rows = len(self.lat_lines) - 1
        cols = len(self.lon_lines) - 1
        all_grid_cell_ids = {
            f"{chr(ord('A') + row)}{col + 1}"
            for row in range(rows)
            for col in range(cols)
        }
        self.prohibited_cells = all_grid_cell_ids - set(self.available_cell_ids)
        self.features_by_id = {feature["id"]: feature for feature in self.features}
        self.features_by_position = {(feature["row"], feature["col"]): feature for feature in self.features}
        self.cells_by_id = {}
        self._matrix = []

        for row in range(rows):
            row_cells = []
            for col in range(cols):
                feature = self.features_by_position[(row, col)]
                cell = Cell(
                    cell_id=feature["id"],
                    row=row,
                    col=col,
                    depth_m=self.depth_by_cell.get(feature["id"], 0.0),
                    colonizable_max_depth_m=self.colonizable_max_depth_m,
                    prohibited=feature["id"] in self.prohibited_cells,
                )
                cell.reset_population()
                row_cells.append(cell)
                self.cells_by_id[cell.cell_id] = cell
            self._matrix.append(row_cells)

        self.colonizable_feature_ids = {
            feature["id"]
            for feature in self.features
            if self.depth_by_cell.get(feature["id"], 0.0) < self.colonizable_max_depth_m
            and feature["id"] not in self.prohibited_cells
        }

    @property
    def rows(self) -> int:
        return len(self.lat_lines) - 1

    @property
    def cols(self) -> int:
        return len(self.lon_lines) - 1

    @property
    def west(self) -> float:
        return min(self.lon_lines)

    @property
    def east(self) -> float:
        return max(self.lon_lines)

    @property
    def south(self) -> float:
        return min(self.lat_lines)

    @property
    def north(self) -> float:
        return max(self.lat_lines)

    @property
    def colonizable_cells(self) -> list[Cell]:
        return [cell for cell in self.iter_cells() if cell.can_be_colonized()]

    @property
    def transport_cells(self) -> list[Cell]:
        return [cell for cell in self.iter_cells() if cell.allows_transport()]

    def total_population(self) -> int:
        return sum(cell.population for cell in self.iter_cells())

    def has_population(self) -> bool:
        return self.total_population() > 0

    def empty_cells_by_id(self) -> dict[str, Cell]:
        return {
            cell_id: Cell(
                cell_id=cell.cell_id,
                row=cell.row,
                col=cell.col,
                depth_m=cell.depth_m,
                colonizable_max_depth_m=cell.colonizable_max_depth_m,
                prohibited=cell.prohibited,
            )
            for cell_id, cell in self.cells_by_id.items()
        }

    def iter_cells(self) -> Iterator[Cell]:
        for row in self._matrix:
            yield from row

    def get_cell(self, cell_id_or_row: str | int, col: int | None = None) -> Cell | None:
        if col is None:
            if not isinstance(cell_id_or_row, str):
                return None
            return self.cells_by_id.get(cell_id_or_row)

        if not isinstance(cell_id_or_row, int):
            return None
        row = cell_id_or_row
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return None
        return self._matrix[row][col]

    def reset(self) -> None:
        for cell in self.iter_cells():
            cell.prohibited = cell.cell_id in self.prohibited_cells
            cell.reset_population()
