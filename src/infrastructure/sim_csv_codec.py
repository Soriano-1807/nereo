import csv
import io

from src.domain.sim_config import DensityMortalityConfig


class SimulationCsvSerializer:
    FIELDNAMES = [
        "record_type",
        "current_month",
        "cell_id",
        "row",
        "col",
        "population_type",
        "sex",
        "age",
        "count",
        "saturation_threshold",
        "juvenile_mortality_multiplier",
        "adult_mortality_multiplier",
        "dead_larvae_total",
        "dead_lionfish_total",
    ]

    def export(self, service) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=self.FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerow(self.build_meta_row(service))

        for cell in service.grid.iter_cells():
            for record in self.build_cell_rows(cell, service.current_month):
                writer.writerow(record)

        return buffer.getvalue()

    def load_into(self, service, csv_text: str) -> dict:
        rows = self.parse_csv(csv_text)
        meta_row, cell_rows = self.split_rows(rows)
        state = self.parse_state(meta_row, cell_rows, service)

        service.reset_simulation()
        service.apply_density_config(state["density_config"])

        simulator = service.simulator
        simulator.current_month = state["current_month"]
        simulator.dead_larvae_count = state["dead_larvae_total"]
        simulator.dead_lionfish_count = state["dead_lionfish_total"]
        simulator.pending_transport = []
        simulator.pending_transport_month = None

        for cell_state in state["cells"]:
            cell = service.grid.get_cell(cell_state["cell_id"])
            if cell_state["population_type"] == "larvae":
                cell.add_larvae(cell_state["sex"], cell_state["count"])
            elif cell_state["population_type"] == "juvenile":
                cell.add_juvenile(cell_state["sex"], cell_state["age"], cell_state["count"])
            else:
                cell.add_adult(cell_state["sex"], cell_state["age"], cell_state["count"])

        simulator.plan_next_transport()
        return {
            "current_month": service.current_month,
            "density_config": state["density_config"].as_dict(),
        }

    def build_meta_row(self, service) -> dict:
        simulator = service.simulator
        return {
            "record_type": "meta",
            "current_month": service.current_month,
            "cell_id": "",
            "row": "",
            "col": "",
            "population_type": "",
            "sex": "",
            "age": "",
            "count": "",
            "saturation_threshold": simulator.density_mortality_config.saturation_threshold,
            "juvenile_mortality_multiplier": simulator.density_mortality_config.juvenile_mortality_multiplier,
            "adult_mortality_multiplier": simulator.density_mortality_config.adult_mortality_multiplier,
            "dead_larvae_total": simulator.dead_larvae_count,
            "dead_lionfish_total": simulator.dead_lionfish_count,
        }

    def build_cell_rows(self, cell, current_month: int) -> list[dict]:
        rows = []

        for sex in ("F", "M"):
            count = cell.larvae_by_sex.get(sex, 0)
            if count > 0:
                rows.append(self.build_population_row(current_month, cell, "larvae", sex, "", count))

        for (sex, age), count in sorted(cell.juveniles_by_sex_age.items(), key=self.population_sort_key):
            if count > 0:
                rows.append(self.build_population_row(current_month, cell, "juvenile", sex, age, count))

        for (sex, age), count in sorted(cell.adults_by_sex_age.items(), key=self.population_sort_key):
            if count > 0:
                rows.append(self.build_population_row(current_month, cell, "adult", sex, age, count))

        return rows

    def build_population_row(self, current_month: int, cell, population_type: str, sex: str, age, count: int) -> dict:
        return {
            "record_type": "cell",
            "current_month": current_month,
            "cell_id": cell.cell_id,
            "row": cell.row,
            "col": cell.col,
            "population_type": population_type,
            "sex": sex,
            "age": age,
            "count": count,
            "saturation_threshold": "",
            "juvenile_mortality_multiplier": "",
            "adult_mortality_multiplier": "",
            "dead_larvae_total": "",
            "dead_lionfish_total": "",
        }

    def population_sort_key(self, item):
        (sex, age), _count = item
        return age, sex

    def parse_csv(self, csv_text: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise ValueError("El archivo CSV esta vacio o no tiene encabezados.")

        missing_fields = [field for field in self.FIELDNAMES if field not in reader.fieldnames]
        if missing_fields:
            raise ValueError("El archivo CSV no tiene el formato esperado.")

        return list(reader)

    def split_rows(self, rows: list[dict]) -> tuple[dict, list[dict]]:
        meta_rows = [row for row in rows if row.get("record_type") == "meta"]
        if len(meta_rows) != 1:
            raise ValueError("El archivo CSV debe tener exactamente una fila meta.")
        cell_rows = [row for row in rows if row.get("record_type") == "cell"]
        return meta_rows[0], cell_rows

    def parse_state(self, meta_row: dict, cell_rows: list[dict], service) -> dict:
        current_month = self.parse_int(meta_row.get("current_month"), "Mes actual invalido.")
        max_simulation_month = service.simulation_parameters.max_simulation_month
        if not 0 <= current_month <= max_simulation_month:
            raise ValueError(f"El mes actual debe estar entre 0 y {max_simulation_month}.")

        density_config = DensityMortalityConfig(
            saturation_threshold=self.parse_int(meta_row.get("saturation_threshold"), "Umbral de saturacion invalido."),
            juvenile_mortality_multiplier=self.parse_float(meta_row.get("juvenile_mortality_multiplier"), "Multiplicador juvenil invalido."),
            adult_mortality_multiplier=self.parse_float(meta_row.get("adult_mortality_multiplier"), "Multiplicador adulto invalido."),
        )

        return {
            "current_month": current_month,
            "density_config": density_config,
            "dead_larvae_total": self.parse_int(meta_row.get("dead_larvae_total"), "Total de larvas muertas invalido."),
            "dead_lionfish_total": self.parse_int(meta_row.get("dead_lionfish_total"), "Total de peces muertos invalido."),
            "cells": [self.parse_cell_row(row, service) for row in cell_rows],
        }

    def parse_cell_row(self, row: dict, service) -> dict:
        population_type = (row.get("population_type") or "").strip()
        if population_type not in {"larvae", "juvenile", "adult"}:
            raise ValueError("El archivo CSV contiene un tipo de poblacion invalido.")

        cell_id = (row.get("cell_id") or "").strip()
        cell = service.grid.get_cell(cell_id)
        if cell is None:
            raise ValueError(f"La celda {cell_id} no existe en la grilla actual.")

        row_index = self.parse_int(row.get("row"), f"Fila invalida para {cell_id}.")
        col_index = self.parse_int(row.get("col"), f"Columna invalida para {cell_id}.")
        if row_index != cell.row or col_index != cell.col:
            raise ValueError(f"La posicion de la celda {cell_id} no coincide con la grilla actual.")

        sex = (row.get("sex") or "").strip()
        if sex not in {"F", "M"}:
            raise ValueError(f"Sexo invalido en la celda {cell_id}.")

        count = self.parse_int(row.get("count"), f"Cantidad invalida en la celda {cell_id}.")
        if count < 0:
            raise ValueError(f"La cantidad en la celda {cell_id} no puede ser negativa.")

        age_value = (row.get("age") or "").strip()
        if population_type == "larvae":
            if age_value:
                raise ValueError(f"La fila de larvas en {cell_id} no debe tener edad.")
            age = None
        else:
            age = self.parse_int(age_value, f"Edad invalida en la celda {cell_id}.")
            if age < 0:
                raise ValueError(f"La edad en la celda {cell_id} no puede ser negativa.")

        return {
            "cell_id": cell_id,
            "population_type": population_type,
            "sex": sex,
            "age": age,
            "count": count,
        }

    def parse_int(self, value, error_message: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(error_message) from None

    def parse_float(self, value, error_message: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(error_message) from None
