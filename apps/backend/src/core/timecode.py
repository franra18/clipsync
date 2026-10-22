import re

TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def to_seconds(time_str: str) -> int:
    """Convierte cadenas de tiempo (MM:SS / HH:MM:SS) a segundos."""
    if not TIME_RE.match(time_str):
        raise ValueError(f"Formato de tiempo inválido: {time_str!r} (usa MM:SS o HH:MM:SS)")
    parts = list(map(int, time_str.split(":")))
    if any(p >= 60 for p in parts[1:]):
        raise ValueError(f"Minutos/segundos fuera de rango: {time_str!r}")
    return sum(p * 60**i for i, p in enumerate(reversed(parts)))
