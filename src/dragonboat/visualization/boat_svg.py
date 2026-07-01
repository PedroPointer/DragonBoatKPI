"""Dragon boat SVG renderer — aerial view with crew positions."""

from __future__ import annotations


def render_boat_svg(
    boat_name: str,
    num_rows: int,
    assignments: list[dict] | None = None,
) -> str:
    """Generate an SVG string for a dragon boat (aerial view).

    boat_name: "DB12" or "DB22"
    num_rows: 5 (DB12) or 10 (DB22)
    assignments: list of {role, side, row_number, nombre, apellido, photo_path}
    """
    assigned: dict[str, dict] = {}
    if assignments:
        for a in assignments:
            key = _pos_key(a["role"], a.get("side"), a.get("row_number"))
            assigned[key] = a

    # Layout — bigger and more elongated
    W = 400
    ROW_H = 56
    PROA_H = 70
    POPA_H = 70
    H = PROA_H + num_rows * ROW_H + POPA_H
    CX = W // 2
    SLOT_R = 20
    HULL_W = 75   # narrower half-width for elongated shape

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                 f'width="{W}" height="{H}" style="max-width:100%;height:auto;">')

    # ── Hull: elongated regular polygon (10-sided) ──
    hull_y0 = PROA_H - 15
    hull_y1 = H - POPA_H + 15
    hull_mid = (hull_y0 + hull_y1) / 2
    hull_h = hull_y1 - hull_y0
    # 10 points: narrow at top/bottom, wide in middle (elongated ellipse)
    import math
    pts = []
    for i in range(10):
        t = i / 9.0
        y = hull_y0 + t * hull_h
        w = HULL_W * math.sin(t * math.pi) ** 0.5
        pts.append(f"{CX - w:.0f},{y:.0f}")
    for i in range(9, -1, -1):
        t = i / 9.0
        y = hull_y0 + t * hull_h
        w = HULL_W * math.sin(t * math.pi) ** 0.5
        pts.append(f"{CX + w:.0f},{y:.0f}")
    hull_poly = " ".join(pts)
    parts.append(f'<polygon points="{hull_poly}" fill="#1e3a5f" stroke="#38bdf8" '
                 f'stroke-width="2.5" opacity="0.5"/>')

    # ── Dragon head (proa) — detailed ──
    hx = CX
    hy = hull_y0
    # Main head shape
    parts.append(
        f'<path d="M {hx},{hy - 40} '
        f'C {hx - 20},{hy - 35} {hx - 35},{hy - 20} {hx - 30},{hy - 5} '
        f'C {hx - 25},{hy + 5} {hx - 10},{hy} {hx},{hy} '
        f'C {hx + 10},{hy} {hx + 25},{hy + 5} {hx + 30},{hy - 5} '
        f'C {hx + 35},{hy - 20} {hx + 20},{hy - 35} {hx},{hy - 40} Z" '
        f'fill="#b91c1c" stroke="#dc2626" stroke-width="2"/>'
    )
    # Snout / lower jaw
    parts.append(
        f'<path d="M {hx - 18},{hy - 10} '
        f'C {hx - 12},{hy + 2} {hx - 5},{hy + 5} {hx},{hy + 3} '
        f'C {hx + 5},{hy + 5} {hx + 12},{hy + 2} {hx + 18},{hy - 10}" '
        f'fill="none" stroke="#991b1b" stroke-width="2"/>'
    )
    # Left horn
    parts.append(
        f'<path d="M {hx - 22},{hy - 28} '
        f'C {hx - 35},{hy - 45} {hx - 30},{hy - 55} {hx - 18},{hy - 50} '
        f'C {hx - 15},{hy - 48} {hx - 18},{hy - 38} {hx - 22},{hy - 28} Z" '
        f'fill="#991b1b" stroke="#dc2626" stroke-width="1"/>'
    )
    # Right horn
    parts.append(
        f'<path d="M {hx + 22},{hy - 28} '
        f'C {hx + 35},{hy - 45} {hx + 30},{hy - 55} {hx + 18},{hy - 50} '
        f'C {hx + 15},{hy - 48} {hx + 18},{hy - 38} {hx + 22},{hy - 28} Z" '
        f'fill="#991b1b" stroke="#dc2626" stroke-width="1"/>'
    )
    # Left eye
    parts.append(f'<circle cx="{hx - 12}" cy="{hy - 22}" r="4" fill="#fbbf24"/>')
    parts.append(f'<circle cx="{hx - 12}" cy="{hy - 22}" r="2" fill="#1a1a1a"/>')
    # Right eye
    parts.append(f'<circle cx="{hx + 12}" cy="{hy - 22}" r="4" fill="#fbbf24"/>')
    parts.append(f'<circle cx="{hx + 12}" cy="{hy - 22}" r="2" fill="#1a1a1a"/>')
    # Nostrils
    parts.append(f'<circle cx="{hx - 6}" cy="{hy - 8}" r="2" fill="#450a0a"/>')
    parts.append(f'<circle cx="{hx + 6}" cy="{hy - 8}" r="2" fill="#450a0a"/>')
    # Flame/crest on top
    parts.append(
        f'<path d="M {hx},{hy - 40} '
        f'C {hx - 5},{hy - 52} {hx - 2},{hy - 58} {hx},{hy - 55} '
        f'C {hx + 2},{hy - 58} {hx + 5},{hy - 52} {hx},{hy - 40} Z" '
        f'fill="#f59e0b" stroke="#fbbf24" stroke-width="1" opacity="0.9"/>'
    )

    # ── Dragon tail (popa) — detailed ──
    tx = CX
    ty = hull_y1
    # Main tail curve
    parts.append(
        f'<path d="M {tx},{ty} '
        f'C {tx - 10},{ty + 15} {tx - 18},{ty + 25} {tx - 12},{ty + 35} '
        f'C {tx - 8},{ty + 42} {tx - 3},{ty + 40} {tx},{ty + 35}" '
        f'fill="none" stroke="#dc2626" stroke-width="4" stroke-linecap="round"/>'
    )
    parts.append(
        f'<path d="M {tx},{ty} '
        f'C {tx + 10},{ty + 15} {tx + 18},{ty + 25} {tx + 12},{ty + 35} '
        f'C {tx + 8},{ty + 42} {tx + 3},{ty + 40} {tx},{ty + 35}" '
        f'fill="none" stroke="#dc2626" stroke-width="4" stroke-linecap="round"/>'
    )
    # Tail fin
    parts.append(
        f'<path d="M {tx - 12},{ty + 35} '
        f'C {tx - 22},{ty + 45} {tx - 15},{ty + 55} {tx},{ty + 48} '
        f'C {tx + 15},{ty + 55} {tx + 22},{ty + 45} {tx + 12},{ty + 35} Z" '
        f'fill="#991b1b" stroke="#dc2626" stroke-width="1.5" opacity="0.85"/>'
    )
    # Tail spikes
    for i, angle_off in enumerate([-18, -8, 8, 18]):
        sx = tx + angle_off
        sy = ty + 10 + i * 2
        parts.append(
            f'<path d="M {sx},{sy} L {sx + (3 if angle_off > 0 else -3)},{sy + 8} '
            f'L {sx},{sy + 5} Z" fill="#b91c1c" stroke="#dc2626" stroke-width="0.5"/>'
        )

    # ── Labels ──
    parts.append(f'<text x="{CX}" y="{hull_y0 - 65}" text-anchor="middle" '
                 f'font-size="12" fill="#94a3b8" font-weight="bold">PROA</text>')
    parts.append(f'<text x="{CX}" y="{hull_y1 + 60}" text-anchor="middle" '
                 f'font-size="12" fill="#94a3b8" font-weight="bold">POPA</text>')

    # ── Tambor (proa) ──
    tambor_y = PROA_H + 8
    _render_slot(parts, CX, tambor_y, SLOT_R, "tambor", None, None, assigned,
                 color="#dc2626")

    # ── Timonel (popa) ──
    timonel_y = H - POPA_H - 8
    _render_slot(parts, CX, timonel_y, SLOT_R, "timonel", None, None, assigned,
                 color="#16a34a")

    # ── Filas de remeros ──
    for row in range(1, num_rows + 1):
        fy = PROA_H + 25 + (row - 1) * ROW_H + ROW_H // 2

        ex = CX - 70
        _render_slot(parts, ex, fy, SLOT_R - 2, "remero", "estribor", row, assigned,
                     color="#d97706", label=f"E{row}")

        bx = CX + 70
        _render_slot(parts, bx, fy, SLOT_R - 2, "remero", "babor", row, assigned,
                     color="#0ea5e9", label=f"B{row}")

        if row < num_rows:
            line_y = fy + ROW_H // 2
            parts.append(f'<line x1="{CX - 50}" y1="{line_y}" x2="{CX + 50}" y2="{line_y}" '
                         f'stroke="#334155" stroke-width="1" stroke-dasharray="4,4" opacity="0.3"/>')

    # ── Column headers ──
    header_y = PROA_H + 25 - 10
    parts.append(f'<text x="{CX - 70}" y="{header_y}" text-anchor="middle" '
                 f'font-size="10" fill="#d97706" font-weight="bold">ESTRIBOR</text>')
    parts.append(f'<text x="{CX + 70}" y="{header_y}" text-anchor="middle" '
                 f'font-size="10" fill="#0ea5e9" font-weight="bold">BABOR</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def _pos_key(role: str, side: str | None, row: int | None) -> str:
    if role == "tambor":
        return "tambor"
    if role == "timonel":
        return "timonel"
    return f"{side}_{row}"


def _render_slot(
    parts: list[str],
    cx: float,
    cy: float,
    r: float,
    role: str,
    side: str | None,
    row: int | None,
    assigned: dict[str, dict],
    color: str = "#334155",
    label: str = "",
) -> None:
    key = _pos_key(role, side, row)
    member = assigned.get(key)

    if member and member.get("photo_path"):
        photo_url = f"/photos/{member['photo_path']}"
        clip_id = f"clip_{key.replace(' ', '_')}"
        parts.append(f'<defs><clipPath id="{clip_id}">'
                     f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'
                     f'</clipPath></defs>')
        parts.append(f'<image href="{photo_url}" x="{cx - r}" y="{cy - r}" '
                     f'width="{r * 2}" height="{r * 2}" clip-path="url(#{clip_id})"/>')
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                     f'stroke="{color}" stroke-width="2.5"/>')
        # Only nombre (first name)
        name = member["nombre"]
        nx = cx + r + 6
        parts.append(f'<text x="{nx}" y="{cy + 4}" font-size="9" fill="#e2e8f0" '
                     f'font-weight="bold">{name}</text>')
    else:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                     f'stroke="{color}" stroke-width="2" stroke-dasharray="4,3" opacity="0.6"/>')
        parts.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" '
                     f'font-size="16" fill="{color}" opacity="0.6">+</text>')
        if label:
            parts.append(f'<text x="{cx}" y="{cy - r - 5}" text-anchor="middle" '
                         f'font-size="9" fill="{color}" opacity="0.8">{label}</text>')
