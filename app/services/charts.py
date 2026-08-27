"""Server-rendered SVG charts: sparklines and larger price charts."""

from __future__ import annotations

from datetime import datetime, timezone

UP_COLOR = "#2fbf71"
DOWN_COLOR = "#e5484d"
GRID_COLOR = "#232c47"
TEXT_COLOR = "#8a94b0"


def _scale(
    values: list[float], width: float, height: float, pad: float
) -> list[tuple[float, float]]:
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = (width - 2 * pad) / max(len(values) - 1, 1)
    return [
        (pad + i * step, height - pad - (v - lo) / span * (height - 2 * pad))
        for i, v in enumerate(values)
    ]


def sparkline(closes: list[float], width: int = 120, height: int = 36) -> str:
    """Compact inline SVG sparkline of recent closes."""
    values = closes[-30:]
    if len(values) < 2:
        return ""
    color = UP_COLOR if values[-1] >= values[0] else DOWN_COLOR
    points = _scale(values, width, height, pad=2)
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="30-day price trend">'
        f'<polyline points="{path}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def price_chart(
    timestamps: list[int],
    closes: list[float],
    width: int = 860,
    height: int = 300,
) -> str:
    """Full price chart with gridlines, axis labels, and area fill."""
    if len(closes) < 2:
        return '<p class="empty-note">Not enough history to chart.</p>'
    color = UP_COLOR if closes[-1] >= closes[0] else DOWN_COLOR
    pad = 44.0
    points = _scale(closes, width, height, pad)
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = (
        f"{points[0][0]:.1f},{height - pad:.1f} "
        + line
        + f" {points[-1][0]:.1f},{height - pad:.1f}"
    )

    lo, hi = min(closes), max(closes)
    rows: list[str] = []
    for frac in (0.0, 0.5, 1.0):
        y = height - pad - frac * (height - 2 * pad)
        value = lo + frac * (hi - lo)
        rows.append(
            f'<line x1="{pad}" y1="{y:.1f}" x2="{width - pad}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOR}" stroke-width="1" stroke-dasharray="3 5"/>'
            f'<text x="{width - pad + 6}" y="{y + 4:.1f}" fill="{TEXT_COLOR}" '
            f'font-size="11">{value:,.0f}</text>'
        )

    labels: list[str] = []
    if timestamps and len(timestamps) == len(closes):
        for frac in (0.0, 0.5, 1.0):
            idx = round(frac * (len(timestamps) - 1))
            x = points[idx][0]
            stamp = datetime.fromtimestamp(timestamps[idx], tz=timezone.utc)
            labels.append(
                f'<text x="{x:.1f}" y="{height - pad + 18:.1f}" fill="{TEXT_COLOR}" '
                f'font-size="11" text-anchor="middle">{stamp.strftime("%b %d")}</text>'
            )

    return (
        f'<svg class="price-chart" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="Price history">'
        f"{''.join(rows)}"
        f'<polygon points="{area}" fill="{color}" opacity="0.08"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f"{''.join(labels)}</svg>"
    )
