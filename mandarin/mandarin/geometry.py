"""Pure wheel geometry (no Qt) so hit-testing is unit-testable."""
from __future__ import annotations

import math

OUTER = 150.0   # fan radius in px
HUB = 46.0      # centre hub radius
GAP_DEG = 3.0   # visual gap between petals


def petal_span(n: int) -> float:
    return 360.0 / max(n, 1)


def petal_at(dx: float, dy: float, n: int) -> int | None:
    """Petal index for an offset from the wheel centre; petal 0 starts at 12 o'clock, clockwise."""
    r = math.hypot(dx, dy)
    if n <= 0 or r < HUB or r > OUTER:
        return None
    ang = (math.degrees(math.atan2(dy, dx)) + 90.0) % 360.0
    return min(int(ang / petal_span(n)), n - 1)


def petal_center(i: int, n: int, radius: float) -> tuple[float, float]:
    mid = math.radians(-90.0 + (i + 0.5) * petal_span(n))
    return radius * math.cos(mid), radius * math.sin(mid)
