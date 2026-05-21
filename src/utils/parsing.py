def parse_non_negative_int(value: object) -> int | None:
    try:
        v = int(value or 0)
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


def parse_positive_int(value: object) -> int | None:
    try:
        v = float(value)
        return int(v) if v > 0 and v.is_integer() else None
    except (TypeError, ValueError):
        return None


def parse_min_float(value: object, minimum: float = 0.0) -> float | None:
    try:
        v = float(value)
        return v if v >= minimum else None
    except (TypeError, ValueError):
        return None
