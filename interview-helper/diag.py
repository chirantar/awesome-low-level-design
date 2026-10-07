#!/usr/bin/env python3
# Usage: diag.py spec.json out.png
# spec: {"title": str,
#        "boxes": {"ID": ["Label\nline2", col, row, "kind"]},
#        "edges": [["A","B","label", "async"?]]}
# kind: svc | db | queue | client | ext  (only shape/color hint)
import json, sys, subprocess, html, math

CW, CH = 250, 160      # grid cell size
BW, BH = 160, 64       # box size
PAD = 40

COLORS = {
    "client": "#dbeafe", "svc": "#dcfce7", "db": "#fee2e2",
    "queue": "#fef3c7", "ext": "#e5e7eb", "gw": "#ede9fe",
}

def center(b):
    _, c, r = b[0], b[1], b[2]
    return PAD + c * CW + BW / 2, PAD + 40 + r * CH + BH / 2

def box_h(b):
    return b[4] * CH - (CH - BH) if len(b) > 4 else BH

def box_w(b):
    return b[5] * CW - (CW - BW) if len(b) > 5 else BW

def border_point(cx, cy, w, h, tx, ty):
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (w / 2) / abs(dx) if dx else math.inf
    sy = (h / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s

def main(spec_path, out):
    spec = json.load(open(spec_path))
    boxes = spec["boxes"]
    maxc = max(b[1] + (b[5] - 1 if len(b) > 5 else 0) for b in boxes.values())
    maxr = max(b[2] + (b[4] - 1 if len(b) > 4 else 0) for b in boxes.values())
    W = PAD * 2 + (maxc + 1) * CW
    H = PAD * 2 + 40 + (maxr + 1) * CH
    geo = {}
    for k, b in boxes.items():
        h = box_h(b)
        x = PAD + b[1] * CW
        y = PAD + 40 + b[2] * CH
        w = box_w(b)
        geo[k] = (x, y, w, h, x + w / 2, y + h / 2)
    svg = []
    svg.append('<defs><marker id="a" viewBox="0 0 10 10" refX="10" refY="5" '
               'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
               '<path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker></defs>')
    svg.append(f'<text x="{PAD}" y="{PAD+10}" font-size="22" font-weight="bold">'
               f'{html.escape(spec.get("title",""))}</text>')
    for e in spec["edges"]:
        a, b = e[0], e[1]
        label = e[2] if len(e) > 2 else ""
        dashed = len(e) > 3 and e[3] == "async"
        ax, ay, aw, ah, acx, acy = geo[a]
        bx, by, bw, bh, bcx, bcy = geo[b]
        x1, y1 = border_point(acx, acy, aw + 8, ah + 8, bcx, bcy)
        x2, y2 = border_point(bcx, bcy, bw + 8, bh + 8, acx, acy)
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#111" '
                   f'stroke-width="1.8"{dash} marker-end="url(#a)"/>')
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            tw = 7.2 * len(label) + 8
            svg.append(f'<rect x="{mx-tw/2}" y="{my-10}" width="{tw}" height="18" '
                       f'fill="#f8fafc" rx="3"/>')
            svg.append(f'<text x="{mx}" y="{my+4}" font-size="13" text-anchor="middle" '
                       f'fill="#1d4ed8">{html.escape(label)}</text>')
    for k, b in boxes.items():
        x, y, w, h, cx, cy = geo[k]
        kind = b[3] if len(b) > 3 else "svc"
        fill = "#ffffff" if spec.get("plain", True) else COLORS.get(kind, "#dcfce7")
        if kind == "db":
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" '
                       f'fill="{fill}" stroke="#111" stroke-width="1.8"/>')
        else:
            svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
                       f'fill="{fill}" stroke="#111" stroke-width="1.8"/>')
        lines = b[0].split("\n")
        start = cy - (len(lines) - 1) * 9 + 5
        for i, ln in enumerate(lines):
            svg.append(f'<text x="{cx}" y="{start + i*18}" font-size="16" '
                       f'text-anchor="middle" font-weight="600">{html.escape(ln)}</text>')
    legend_y = H - 14
    svg.append(f'<text x="{PAD}" y="{legend_y}" font-size="14" fill="#444">'
               f'solid = sync call   dashed = async / CDC via Kafka</text>')
    doc = (f'<html><body style="margin:0;background:#f8fafc">'
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="DejaVu Sans, sans-serif">{"".join(svg)}</svg></body></html>')
    hp = out.rsplit(".", 1)[0] + ".html"
    open(hp, "w").write(doc)
    subprocess.run([
        "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
        "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}",
        "--force-device-scale-factor=2", "--virtual-time-budget=2000", f"--screenshot={out}", "file://" + __import__("os").path.abspath(hp),
    ], check=True, capture_output=True)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
