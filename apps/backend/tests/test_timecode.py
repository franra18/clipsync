# Ejecutar desde apps/backend:  python -m tests.test_timecode
from src.core.timecode import to_seconds

assert to_seconds("00:05") == 5
assert to_seconds("01:30") == 90
assert to_seconds("1:02:03") == 3723
assert to_seconds("10:00:00") == 36000

for bad in ["", "5", "1:2", "00:60", "1:60:00", "aa:bb", "1:00:00:00"]:
    try:
        to_seconds(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"debería fallar: {bad!r}")

print("OK")
