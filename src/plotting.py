"""Small accessible SVG charts; no fabricated placeholders."""

import html
from pathlib import Path


def funnel_svg(rows, path):
    rows = sorted([r for r in rows if r["grain"] == "ordered_sessions"], key=lambda r: r["stage"])
    labels = ["View item", "Add to cart", "Begin checkout", "Purchase"]
    maximum = max([r["reached"] for r in rows], default=1) or 1
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-label="Ordered session funnel">',
        '<rect width="760" height="300" fill="#101e2b"/>',
    ]
    for i, row in enumerate(rows):
        y = 24 + i * 66
        parts += [
            f'<text x="15" y="{y + 22}" fill="#e5eef3" font-family="sans-serif" font-size="15">{labels[row["stage"] - 1]}</text>',
            f'<rect x="155" y="{y}" width="{480 * row["reached"] / maximum:.2f}" height="36" rx="5" fill="#64d9bd"/>',
            f'<text x="650" y="{y + 23}" fill="#e5eef3" font-family="sans-serif">{row["reached"]:,}</text>',
        ]
    Path(path).write_text("".join(parts) + "</svg>", encoding="utf-8")


def retention_svg(rows, path):
    rows = [r for r in rows if r["dimension"] == "all"]
    weeks = sorted({r["cohort_week"] for r in rows})
    lookup = {(r["cohort_week"], r["horizon"]): r for r in rows}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" viewBox="0 0 600 {70 + 40 * len(weeks)}" role="img" aria-label="Exact-day retention heatmap">'
    ]
    for j, h in enumerate([1, 7, 14, 30]):
        parts.append(f'<text x="{190 + j * 100}" y="25" fill="#e5eef3">D{h}</text>')
    for i, week in enumerate(weeks):
        y = 45 + i * 40
        parts.append(f'<text x="10" y="{y + 23}" fill="#e5eef3">{html.escape(week)}</text>')
        for j, h in enumerate([1, 7, 14, 30]):
            row = lookup.get((week, h))
            publish = row is not None and row["eligible_users"] >= 100
            value = row["retention"] if publish else 0
            label = f"{value:.1%}" if publish else "—"
            fill = f"hsl(163 55% {14 + min(value * 160, 58):.1f}%)" if publish else "#253341"
            parts += [
                f'<rect x="{160 + j * 100}" y="{y}" width="94" height="34" rx="4" fill="{fill}"/>',
                f'<text x="{178 + j * 100}" y="{y + 23}" fill="white">{label}</text>',
            ]
    Path(path).write_text("".join(parts) + "</svg>", encoding="utf-8")
