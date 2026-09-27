#!/usr/bin/env python3
"""
Generates the flat, grainy cartoon illustrations used by the DTS website.

Style notes (matching the reference sample): limited earthy palette, flat shapes,
no outlines, a light paper-grain texture over everything, a floor band at the
bottom, calm faces (closed eyes + small smile).

Run:  python3 tools/make_illustrations.py
Output goes to assets/illustrations/*.svg
"""
import os, math

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "illustrations")
os.makedirs(OUT, exist_ok=True)

# ---- palette --------------------------------------------------------------
P = dict(
    green="#2F5D3C", teal="#3E6B6F", ochre="#B8622B", olive="#5E6E38",
    slate="#46587A", plum="#6A4C6E", rust="#9A4A2A",
    sand="#EAD9A6", cream="#F4E8CC", yellow="#E9C46A", ink="#1C2627",
    light="#F7F1E1", mint="#BFD8B0", coral="#F2B8A0", sky="#9BC2C6",
    dark="#17211F",
)
SKIN = ["#F1C9A5", "#D9A06B", "#A86B44", "#6E4630", "#E8B48C"]
HAIR = ["#1C2627", "#3B2A20", "#C98A3A", "#7A3B22", "#5B4636"]

def defs():
    return """<defs>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
</defs>"""

def grain(w, h):
    return f'<rect width="{w}" height="{h}" filter="url(#grain)" opacity="0.16" style="mix-blend-mode:multiply"/>'

def svg(w, h, bg, body, floor=True, floor_h=58):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">',
             defs(),
             f'<rect width="{w}" height="{h}" rx="22" fill="{bg}"/>']
    if floor:
        parts.append(f'<path d="M0 {h-floor_h} Q {w/2} {h-floor_h-14} {w} {h-floor_h} V {h-22} Q {w} {h} {w-22} {h} H 22 Q 0 {h} 0 {h-22} Z" fill="{P["sand"]}"/>')
    parts.append(body)
    parts.append(grain(w, h))
    parts.append("</svg>")
    return "\n".join(parts)

# ---- character parts (local coords: feet/hips at origin, y up is negative) --
def face(hx, hy, r, skin, mood="calm", flip=False):
    """Closed calm eyes + smile. hx,hy = head centre."""
    ey = hy + r*0.05
    dx = r*0.42
    s = f'<circle cx="{hx}" cy="{hy}" r="{r}" fill="{skin}"/>'
    if mood == "calm":
        s += (f'<path d="M{hx-dx-4} {ey} q4 3 8 0" stroke="{P["ink"]}" stroke-width="2" fill="none" stroke-linecap="round"/>'
              f'<path d="M{hx+dx-4} {ey} q4 3 8 0" stroke="{P["ink"]}" stroke-width="2" fill="none" stroke-linecap="round"/>')
    else:  # open
        s += f'<circle cx="{hx-dx}" cy="{ey}" r="2.2" fill="{P["ink"]}"/><circle cx="{hx+dx}" cy="{ey}" r="2.2" fill="{P["ink"]}"/>'
    s += f'<path d="M{hx-5} {hy+r*0.45} q5 4 10 0" stroke="{P["ink"]}" stroke-width="2" fill="none" stroke-linecap="round"/>'
    s += f'<circle cx="{hx-r*0.62}" cy="{hy+r*0.35}" r="3" fill="{P["coral"]}" opacity="0.55"/><circle cx="{hx+r*0.62}" cy="{hy+r*0.35}" r="3" fill="{P["coral"]}" opacity="0.55"/>'
    return s

def hair(style, hx, hy, r, col):
    if style == "short":
        return f'<path d="M{hx-r} {hy} a{r} {r} 0 0 1 {2*r} 0 v-{r*0.15} q-{r*0.3} -{r*0.5} -{r} -{r*0.55} q-{r*0.7} 0 -{r} {r*0.55} z" fill="{col}"/>'
    if style == "bun":
        return (f'<circle cx="{hx+r*0.35}" cy="{hy-r*1.05}" r="{r*0.42}" fill="{col}"/>'
                f'<path d="M{hx-r-2} {hy+2} a{r+2} {r+2} 0 0 1 {2*r+4} 0 q-{r*0.2} -{r*0.65} -{r+2} -{r*0.7} q-{r*0.9} 0.1 -{r+2} {r*0.7} z" fill="{col}"/>')
    if style == "long":   # front fringe only; back panel drawn by hair_back()
        return f'<path d="M{hx-r-1} {hy+2} a{r+1} {r+1} 0 0 1 {2*r+2} 0 q-{r*0.15} -{r*0.6} -{r*0.7} -{r*0.7} q-{r*0.9} 0 -{r*1.3} {r*0.7} z" fill="{col}"/>'
    if style == "curly":
        s = ""
        for i in range(7):
            a = math.pi*(1.05 + i*0.15)
            s += f'<circle cx="{hx+math.cos(a)*r*0.95:.1f}" cy="{hy+math.sin(a)*r*0.95:.1f}" r="{r*0.42:.1f}" fill="{col}"/>'
        return s
    if style == "bob":    # front fringe only; back panel drawn by hair_back()
        return f'<path d="M{hx-r-2} {hy+1} a{r+2} {r+2} 0 0 1 {2*r+4} 0 q-{r*0.2} -{r*0.55} -{r*0.6} -{r*0.6} q-{r*0.8} 0 -{r*1.4} {r*0.6} z" fill="{col}"/>'
    if style == "kid":
        return f'<path d="M{hx-r} {hy-2} a{r} {r} 0 0 1 {2*r} 0 q-{r*0.25} -{r*0.55} -{r*0.7} -{r*0.7} q-{r*0.5} -{r*0.15} -{r*0.55} {r*0.2} q-{r*0.5} -{r*0.1} -{r*0.75} {r*0.5} z" fill="{col}"/>'
    if style == "puffs":
        return (f'<circle cx="{hx-r*0.75}" cy="{hy-r*0.85}" r="{r*0.5}" fill="{col}"/><circle cx="{hx+r*0.75}" cy="{hy-r*0.85}" r="{r*0.5}" fill="{col}"/>'
                f'<path d="M{hx-r} {hy} a{r} {r} 0 0 1 {2*r} 0 q-{r*0.3} -{r*0.5} -{r} -{r*0.5} q-{r*0.7} 0 -{r} {r*0.5} z" fill="{col}"/>')
    return ""

def hair_back(style, hx, hy, r, col):
    if style == "long":
        return f'<rect x="{hx-r-3}" y="{hy-r-3}" width="{2*r+6}" height="{r*2.9}" rx="{r+3}" fill="{col}"/>'
    if style == "bob":
        return f'<rect x="{hx-r-2}" y="{hy-r-2}" width="{2*r+4}" height="{r*2.2}" rx="{r+2}" fill="{col}"/>'
    return ""

def arm(x1, y1, x2, y2, col, w=13, skin=None, via=None):
    if via:
        d = f'M{x1} {y1} Q{via[0]} {via[1]} {x2} {y2}'
    else:
        d = f'M{x1} {y1} L{x2} {y2}'
    s = f'<path d="{d}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round"/>'
    if skin:
        s += f'<circle cx="{x2}" cy="{y2}" r="{w*0.55}" fill="{skin}"/>'
    return s

def person(x, y, scale=1.0, skin=SKIN[0], hair_col=HAIR[0], hair_style="short",
           top=P["yellow"], bottom=P["ink"], pose="stand", flip=False,
           arms="down", mood="calm", extra=""):
    """Returns an SVG group. Origin: standing/kneel -> feet centre; sit -> hips."""
    parts = []
    r = 20
    if pose == "stand":
        # legs
        parts.append(f'<rect x="-17" y="-84" width="15" height="84" rx="7" fill="{bottom}"/>')
        parts.append(f'<rect x="2" y="-84" width="15" height="84" rx="7" fill="{bottom}"/>')
        parts.append(f'<ellipse cx="-9" cy="0" rx="12" ry="5" fill="{P["dark"]}"/><ellipse cx="10" cy="0" rx="12" ry="5" fill="{P["dark"]}"/>')
        # torso
        parts.append(f'<path d="M-28 -136 q0 -10 10 -10 h36 q10 0 10 10 l-3 58 h-50 z" fill="{top}"/>')
        parts.append(f'<rect x="-6" y="-152" width="12" height="16" fill="{skin}"/>')
        hy = -164
        sh = (-24, -132), (24, -132)
        if arms == "down":
            parts.append(arm(sh[0][0], sh[0][1], -30, -78, top, skin=skin))
            parts.append(arm(sh[1][0], sh[1][1], 30, -78, top, skin=skin))
        elif arms == "wave":
            parts.append(arm(sh[0][0], sh[0][1], -30, -78, top, skin=skin))
            parts.append(arm(sh[1][0], sh[1][1], 46, -170, top, skin=skin, via=(48, -125)))
        elif arms == "hold_front":   # holding something (clipboard/tablet) at chest
            parts.append(arm(sh[0][0], sh[0][1], -8, -104, top, skin=skin, via=(-34, -100)))
            parts.append(arm(sh[1][0], sh[1][1], 12, -104, top, skin=skin, via=(36, -100)))
        elif arms == "point":
            parts.append(arm(sh[0][0], sh[0][1], -30, -78, top, skin=skin))
            parts.append(arm(sh[1][0], sh[1][1], 62, -142, top, skin=skin))
        elif arms == "reach_up_right":  # child reaching up to hold an adult's hand
            parts.append(arm(sh[0][0], sh[0][1], -30, -78, top, skin=skin))
            parts.append(arm(sh[1][0], sh[1][1], 50, -108, top, skin=skin))
        elif arms == "hold_hand_left":  # arm reaching down-left (holding a child's hand)
            parts.append(arm(sh[0][0], sh[0][1], -46, -66, top, skin=skin))
            parts.append(arm(sh[1][0], sh[1][1], 30, -78, top, skin=skin))
    elif pose == "sit_floor":
        # crossed legs blob
        parts.append(f'<ellipse cx="0" cy="8" rx="44" ry="18" fill="{bottom}"/>')
        parts.append(f'<ellipse cx="-38" cy="14" rx="11" ry="6" fill="{P["dark"]}"/><ellipse cx="38" cy="14" rx="11" ry="6" fill="{P["dark"]}"/>')
        parts.append(f'<path d="M-27 -62 q0 -10 10 -10 h34 q10 0 10 10 l-2 62 h-50 z" fill="{top}"/>')
        parts.append(f'<rect x="-6" y="-78" width="12" height="16" fill="{skin}"/>')
        hy = -90
        sh = (-23, -58), (23, -58)
        if arms == "down":
            parts.append(arm(*sh[0], -34, -6, top, skin=skin))
            parts.append(arm(*sh[1], 34, -6, top, skin=skin))
        elif arms == "reach_right":
            parts.append(arm(*sh[0], -34, -6, top, skin=skin))
            parts.append(arm(*sh[1], 62, -22, top, skin=skin, via=(45, -50)))
        elif arms == "reach_both":
            parts.append(arm(*sh[0], -56, -18, top, skin=skin, via=(-45, -48)))
            parts.append(arm(*sh[1], 56, -18, top, skin=skin, via=(45, -48)))
        elif arms == "lap":
            parts.append(arm(*sh[0], -6, -12, top, skin=skin, via=(-36, -22)))
            parts.append(arm(*sh[1], 8, -12, top, skin=skin, via=(36, -22)))
    elif pose == "sit_chair":  # facing +x
        parts.append(f'<rect x="-6" y="-8" width="52" height="16" rx="8" fill="{bottom}"/>')
        parts.append(f'<rect x="32" y="0" width="15" height="58" rx="7" fill="{bottom}"/>')
        parts.append(f'<ellipse cx="44" cy="58" rx="12" ry="5" fill="{P["dark"]}"/>')
        parts.append(f'<path d="M-26 -66 q0 -10 10 -10 h34 q10 0 10 10 l-2 66 h-50 z" fill="{top}"/>')
        parts.append(f'<rect x="-6" y="-82" width="12" height="16" fill="{skin}"/>')
        hy = -94
        sh = (-22, -62), (22, -62)
        if arms == "lap":
            parts.append(arm(*sh[0], 22, -12, top, skin=skin, via=(-20, -20)))
            parts.append(arm(*sh[1], 30, -14, top, skin=skin, via=(34, -40)))
        elif arms == "table":
            parts.append(arm(*sh[0], 40, -34, top, skin=skin, via=(0, -30)))
            parts.append(arm(*sh[1], 50, -36, top, skin=skin, via=(42, -50)))
        elif arms == "cup":
            parts.append(arm(*sh[0], 10, -14, top, skin=skin, via=(-22, -18)))
            parts.append(arm(*sh[1], 26, -44, top, skin=skin, via=(40, -46)))
        elif arms == "wave":
            parts.append(arm(*sh[0], 22, -12, top, skin=skin, via=(-20, -20)))
            parts.append(arm(*sh[1], 50, -100, top, skin=skin, via=(48, -60)))
    elif pose == "kneel":  # facing +x, knees on floor
        parts.append(f'<rect x="-14" y="-40" width="18" height="40" rx="8" fill="{bottom}"/>')
        parts.append(f'<rect x="-14" y="-14" width="52" height="16" rx="8" fill="{bottom}"/>')
        parts.append(f'<ellipse cx="38" cy="-2" rx="12" ry="6" fill="{P["dark"]}"/>')
        parts.append(f'<path d="M-26 -104 q0 -10 10 -10 h34 q10 0 10 10 l-2 66 h-50 z" fill="{top}"/>')
        parts.append(f'<rect x="-6" y="-120" width="12" height="16" fill="{skin}"/>')
        hy = -132
        sh = (-22, -100), (22, -100)
        if arms == "reach_right":
            parts.append(arm(*sh[0], -24, -48, top, skin=skin))
            parts.append(arm(*sh[1], 66, -60, top, skin=skin, via=(48, -90)))
        else:
            parts.append(arm(*sh[0], -24, -48, top, skin=skin))
            parts.append(arm(*sh[1], 40, -50, top, skin=skin, via=(34, -80)))
    parts.insert(0, hair_back(hair_style, 0, hy, r, hair_col))
    parts.append(face(0, hy, r, skin, mood))
    parts.append(hair(hair_style, 0, hy, r, hair_col))
    parts.append(extra)
    sx = -scale if flip else scale
    return f'<g transform="translate({x} {y}) scale({sx} {scale})">' + "".join(parts) + "</g>"

# ---- props ---------------------------------------------------------------
def plant(x, y, s=1.0, pot=P["cream"], leaf=P["mint"], dark=P["dark"]):
    return f'''<g transform="translate({x} {y}) scale({s})">
  <path d="M0 0 c-30 -20 -22 -60 -8 -72 c10 20 8 44 8 72z" fill="{leaf}"/>
  <path d="M0 0 c30 -20 24 -62 6 -76 c-12 24 -10 50 -6 76z" fill="{dark}"/>
  <path d="M0 0 c-4 -30 8 -70 24 -84 c4 30 -6 60 -24 84z" fill="{leaf}"/>
  <path d="M0 0 c2 -28 -14 -62 -30 -70 c0 28 12 52 30 70z" fill="{dark}"/>
  <path d="M-18 -2 h36 l-5 34 h-26z" fill="{pot}"/>
  <circle cx="-4" cy="14" r="4" fill="{P['ink']}"/><circle cx="8" cy="22" r="3" fill="{P['ink']}"/>
</g>'''

def blocks(x, y, s=1.0):
    return f'''<g transform="translate({x} {y}) scale({s})">
  <rect x="-40" y="-26" width="26" height="26" rx="4" fill="{P['yellow']}"/>
  <rect x="-12" y="-26" width="26" height="26" rx="4" fill="{P['coral']}"/>
  <rect x="-26" y="-52" width="26" height="26" rx="4" fill="{P['sky']}"/>
  <rect x="-26" y="-78" width="26" height="26" rx="4" fill="{P['cream']}"/>
  <rect x="20" y="-26" width="26" height="26" rx="4" fill="{P['mint']}"/>
  <circle cx="-13" cy="-65" r="5" fill="{P['ochre']}"/>
  <path d="M-27 -13 l4 -4 l4 4 l-4 4z" fill="{P['ink']}" opacity=".6"/>
</g>'''

def star(x, y, r, col):
    pts = []
    for i in range(10):
        a = -math.pi/2 + i*math.pi/5
        rr = r if i % 2 == 0 else r*0.45
        pts.append(f"{x+math.cos(a)*rr:.1f},{y+math.sin(a)*rr:.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{col}"/>'

def table(x, y, w=200, col=P["cream"], legs=P["dark"]):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="6" fill="{col}"/>'
            f'<rect x="{x+14}" y="{y+10}" width="8" height="70" fill="{legs}"/>'
            f'<rect x="{x+w-22}" y="{y+10}" width="8" height="70" fill="{legs}"/>')

def chair(x, y, col=P["cream"], w=70):
    # armchair, hips at (x,y) area; drawn behind the person
    return f'''<g transform="translate({x} {y})">
  <rect x="-44" y="-96" width="20" height="120" rx="10" fill="{col}"/>
  <rect x="-44" y="-20" width="{w+30}" height="56" rx="14" fill="{col}"/>
  <rect x="{w-30}" y="-36" width="20" height="70" rx="10" fill="{col}"/>
  <rect x="-30" y="36" width="10" height="20" fill="{P['dark']}"/><rect x="{w-16}" y="36" width="10" height="20" fill="{P['dark']}"/>
</g>'''

def speech(x, y, col=P["cream"], flip=False, dots=True):
    sx = -1 if flip else 1
    d = ""
    if dots:
        d = f'<circle cx="-12" cy="0" r="3.5" fill="{P["ink"]}"/><circle cx="0" cy="0" r="3.5" fill="{P["ink"]}"/><circle cx="12" cy="0" r="3.5" fill="{P["ink"]}"/>'
    return f'<g transform="translate({x} {y}) scale({sx} 1)"><path d="M-30 -18 q0 -10 10 -10 h40 q10 0 10 10 v22 q0 10 -10 10 h-22 l-12 12 v-12 h-6 q-10 0 -10 -10z" fill="{col}"/>{d}</g>'

def heart(x, y, s, col):
    return f'<path transform="translate({x} {y}) scale({s})" d="M0 6 C-14 -6 -10 -18 0 -12 C10 -18 14 -6 0 6z" fill="{col}"/>'

def sun(x, y, r, col=P["yellow"]):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>'

def window(x, y, w=110, h=90, frame=P["cream"], sky=P["sky"]):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{frame}"/>'
            f'<rect x="{x+8}" y="{y+8}" width="{w-16}" height="{h-16}" rx="6" fill="{sky}"/>'
            f'<rect x="{x+w/2-3}" y="{y+8}" width="6" height="{h-16}" fill="{frame}"/>'
            f'<rect x="{x+8}" y="{y+h/2-3}" width="{w-16}" height="6" fill="{frame}"/>'
            f'<circle cx="{x+w-30}" cy="{y+30}" r="10" fill="{P["yellow"]}"/>')

# ---- scenes ----------------------------------------------------------------
W, H = 400, 300
FLOOR = H - 58   # y of floor top

scenes = {}

# 1. ABA therapy: therapist + child on floor with blocks, star sticker
scenes["aba-therapy"] = svg(W, H, P["green"],
    window(40, 40, 100, 80) +
    person(300, FLOOR+6, 0.95, SKIN[1], HAIR[0], "bun", P["yellow"], P["ink"], "sit_floor", flip=True, arms="reach_right") +
    person(110, FLOOR+8, 0.68, SKIN[3], HAIR[0], "puffs", P["coral"], P["slate"], "sit_floor", arms="reach_right", mood="open") +
    blocks(205, FLOOR+8, 1.0) +
    star(330, 70, 14, P["yellow"]) + star(360, 100, 8, P["cream"]) +
    plant(370, FLOOR+6, 0.55)
)

# 2. Assessment & treatment planning: BCBA with clipboard, chart on wall, child playing
scenes["assessment"] = svg(W, H, P["teal"],
    # wall chart
    f'<rect x="230" y="36" width="130" height="96" rx="10" fill="{P["cream"]}"/>' +
    f'<rect x="250" y="100" width="16" height="20" rx="3" fill="{P["ochre"]}"/><rect x="274" y="84" width="16" height="36" rx="3" fill="{P["yellow"]}"/>' +
    f'<rect x="298" y="70" width="16" height="50" rx="3" fill="{P["green"]}"/><rect x="322" y="54" width="16" height="66" rx="3" fill="{P["teal"]}"/>' +
    f'<path d="M258 92 L282 76 L306 60 L330 46" stroke="{P["ink"]}" stroke-width="3" fill="none" stroke-linecap="round" opacity=".7"/>' +
    person(120, FLOOR+2, 0.95, SKIN[0], HAIR[3], "long", P["cream"], P["slate"], "stand", arms="hold_front",
           extra=f'<g transform="translate(-16 -124)"><rect width="34" height="44" rx="4" fill="{P["ochre"]}"/><rect x="4" y="6" width="26" height="34" rx="2" fill="{P["light"]}"/>'
                 f'<path d="M9 16 l4 4 l8 -8" stroke="{P["green"]}" stroke-width="3" fill="none" stroke-linecap="round"/>'
                 f'<path d="M9 28 l4 4 l8 -8" stroke="{P["green"]}" stroke-width="3" fill="none" stroke-linecap="round"/></g>') +
    person(295, FLOOR+8, 0.6, SKIN[2], HAIR[1], "kid", P["mint"], P["ochre"], "sit_floor", arms="lap", mood="open") +
    f'<circle cx="335" cy="{FLOOR-4}" r="10" fill="{P["yellow"]}"/><circle cx="356" cy="{FLOOR-2}" r="7" fill="{P["coral"]}"/>'
)

# 3. Parent & caregiver training: parent and child at table, high five
scenes["parent-training"] = svg(W, H, P["ochre"],
    sun(330, 70, 34, P["yellow"]) +
    table(60, FLOOR-52, 200, P["cream"]) +
    person(96, FLOOR-52, 0.9, SKIN[4], HAIR[4], "short", P["teal"], P["ink"], "sit_chair", arms="wave") +
    person(232, FLOOR-52, 0.62, SKIN[1], HAIR[0], "puffs", P["yellow"], P["slate"], "sit_chair", flip=True, arms="wave", mood="open") +
    star(178, 92, 10, P["cream"]) + star(196, 76, 6, P["cream"]) + star(160, 76, 6, P["cream"]) +
    f'<rect x="120" y="{FLOOR-64}" width="26" height="10" rx="3" fill="{P["sky"]}"/><rect x="150" y="{FLOOR-66}" width="22" height="12" rx="3" fill="{P["mint"]}"/>' +
    plant(370, FLOOR+6, 0.6)
)

# 4. Early intervention: toddler with shape sorter, adult kneeling
scenes["early-intervention"] = svg(W, H, P["olive"],
    window(250, 40, 110, 80) +
    person(120, FLOOR+4, 0.9, SKIN[2], HAIR[0], "curly", P["coral"], P["ink"], "kneel", arms="reach_right") +
    person(270, FLOOR+10, 0.55, SKIN[0], HAIR[2], "kid", P["sky"], P["ochre"], "sit_floor", flip=True, arms="reach_right", mood="open") +
    # shape sorter
    f'<g transform="translate(190 {FLOOR-6})"><rect x="-24" y="-30" width="52" height="34" rx="6" fill="{P["yellow"]}"/>'
    f'<circle cx="-10" cy="-14" r="6" fill="{P["ink"]}" opacity=".5"/><rect x="4" y="-20" width="12" height="12" fill="{P["ink"]}" opacity=".5"/>'
    f'<circle cx="-40" cy="-6" r="7" fill="{P["coral"]}"/><rect x="34" y="-14" width="13" height="13" rx="2" fill="{P["mint"]}"/></g>' +
    f'<path d="M60 90 l10 -6 l10 6 l-10 6z" fill="{P["cream"]}"/><circle cx="90" cy="70" r="5" fill="{P["yellow"]}"/>'
)

# 5. Social skills: three kids in a circle with a ball
scenes["social-skills"] = svg(W, H, P["slate"],
    sun(70, 64, 30, P["yellow"]) +
    person(90, FLOOR+8, 0.68, SKIN[3], HAIR[0], "puffs", P["yellow"], P["ochre"], "sit_floor", arms="reach_right", mood="open") +
    person(200, FLOOR-6, 0.6, SKIN[0], HAIR[3], "bob", P["mint"], P["ink"], "sit_floor", arms="reach_both", mood="open") +
    person(312, FLOOR+8, 0.68, SKIN[1], HAIR[1], "kid", P["coral"], P["teal"], "sit_floor", flip=True, arms="reach_right", mood="open") +
    f'<circle cx="200" cy="{FLOOR+4}" r="22" fill="{P["cream"]}"/><path d="M182 {FLOOR-2} q18 -8 36 0 M182 {FLOOR+10} q18 8 36 0" stroke="{P["ochre"]}" stroke-width="4" fill="none" stroke-linecap="round"/>' +
    speech(258, 96, P["cream"], flip=True) + heart(150, 100, 1.6, P["coral"])
)

# 6. School consultation: teacher at board with shapes, child at desk
scenes["school-consultation"] = svg(W, H, P["plum"],
    f'<rect x="40" y="36" width="170" height="110" rx="10" fill="{P["dark"]}"/><rect x="40" y="36" width="170" height="110" rx="10" fill="none" stroke="{P["cream"]}" stroke-width="6"/>' +
    f'<circle cx="80" cy="76" r="14" fill="none" stroke="{P["yellow"]}" stroke-width="4"/><rect x="112" y="62" width="28" height="28" fill="none" stroke="{P["sky"]}" stroke-width="4"/>' +
    f'<path d="M160 90 l16 -28 l16 28z" fill="none" stroke="{P["coral"]}" stroke-width="4" stroke-linejoin="round"/>' +
    f'<path d="M70 118 h110" stroke="{P["cream"]}" stroke-width="4" stroke-linecap="round" opacity=".6"/><path d="M70 130 h70" stroke="{P["cream"]}" stroke-width="4" stroke-linecap="round" opacity=".6"/>' +
    person(258, FLOOR+2, 0.92, SKIN[1], HAIR[0], "bun", P["cream"], P["teal"], "stand", flip=True, arms="point") +
    table(300, FLOOR-46, 90, P["cream"]) +
    person(330, FLOOR-46, 0.6, SKIN[4], HAIR[1], "kid", P["yellow"], P["ink"], "sit_chair", arms="table", mood="open") +
    f'<rect x="350" y="{FLOOR-58}" width="30" height="10" rx="2" fill="{P["mint"]}"/>'
)

# 7. Counseling: adult in armchair with cup, plant, calm
scenes["counseling"] = svg(W, H, P["green"],
    window(230, 34, 120, 92) +
    chair(150, FLOOR-10, P["cream"], 80) +
    person(150, FLOOR-24, 0.95, SKIN[0], HAIR[2], "long", P["teal"], P["ink"], "sit_chair", arms="cup",
           extra=f'<rect x="16" y="-56" width="22" height="20" rx="4" fill="{P["ochre"]}"/><path d="M38 -50 q10 0 10 8 q0 8 -10 8" stroke="{P["ochre"]}" stroke-width="4" fill="none"/>'
                 f'<path d="M22 -64 q3 -6 0 -12 M30 -64 q3 -6 0 -12" stroke="{P["cream"]}" stroke-width="2" fill="none" stroke-linecap="round" opacity=".8"/>') +
    plant(60, FLOOR+6, 0.9) +
    speech(300, 160, P["yellow"], flip=True, dots=False) + heart(300, 160, 1.4, P["ochre"])
)

# 8. Telehealth: laptop with video call
scenes["telehealth"] = svg(W, H, P["teal"],
    table(40, FLOOR-40, 320, P["cream"]) +
    # laptop
    f'<g transform="translate(200 {FLOOR-40})"><rect x="-96" y="-120" width="192" height="118" rx="10" fill="{P["dark"]}"/>'
    f'<rect x="-86" y="-110" width="172" height="98" rx="6" fill="{P["sand"]}"/><rect x="-110" y="-4" width="220" height="10" rx="5" fill="{P["ink"]}"/>'
    # two tiles
    f'<rect x="-82" y="-106" width="82" height="90" rx="6" fill="{P["green"]}"/><rect x="0" y="-106" width="82" height="90" rx="6" fill="{P["ochre"]}"/>'
    + person(-41, -22, 0.36, SKIN[1], HAIR[0], "bun", P["yellow"], P["ink"], "sit_floor", arms="wave" if False else "lap")
    + person(41, -22, 0.36, SKIN[0], HAIR[3], "short", P["cream"], P["ink"], "sit_floor", arms="lap", mood="open")
    + f'<circle cx="-70" cy="-96" r="4" fill="{P["coral"]}"/></g>' +
    f'<rect x="326" y="{FLOOR-64}" width="18" height="24" rx="4" fill="{P["yellow"]}"/><path d="M344 -0" />' +
    plant(60, FLOOR-42, 0.5) +
    f'<path d="M110 60 q14 -12 28 0 M104 50 q20 -18 40 0" stroke="{P["cream"]}" stroke-width="4" fill="none" stroke-linecap="round" opacity=".7"/>' +
    f'<circle cx="124" cy="70" r="4" fill="{P["cream"]}" opacity=".7"/>'
)

# 9. Hero: adult walking hand-in-hand with child towards a big sun
HW, HH = 560, 420
HF = HH - 70
scenes["hero"] = svg(HW, HH, P["green"],
    sun(400, 150, 90, P["yellow"]) +
    f'<path d="M0 {HF} Q140 {HF-40} 280 {HF} T560 {HF}" fill="{P["olive"]}" opacity=".55"/>' +
    person(220, HF+2, 1.05, SKIN[1], HAIR[0], "bun", P["cream"], P["teal"], "stand", arms="hold_hand_left") +
    person(142, HF+4, 0.62, SKIN[3], HAIR[0], "puffs", P["yellow"], P["ochre"], "stand", arms="reach_up_right", mood="open") +
    plant(470, HF+6, 1.1) + plant(60, HF+6, 0.7) +
    heart(280, 118, 2.2, P["coral"]) + star(330, 70, 12, P["cream"]) + star(120, 110, 8, P["cream"]),
    floor_h=70)

# 10..12 Who-we-help cards (tall, like the reference)
CW, CH = 360, 300
CF = CH - 60
scenes["card-children"] = svg(CW, CH, P["green"],
    person(120, CF+8, 0.7, SKIN[2], HAIR[1], "kid", P["yellow"], P["slate"], "sit_floor", arms="reach_right", mood="open") +
    blocks(210, CF+8, 0.9) + star(290, 70, 12, P["yellow"]) + plant(320, CF+6, 0.55))
scenes["card-teens"] = svg(CW, CH, P["teal"],
    person(180, CF+8, 0.95, SKIN[1], HAIR[0], "curly", P["coral"], P["ink"], "sit_floor", arms="lap",
           extra=f'<rect x="-20" y="-30" width="40" height="28" rx="4" fill="{P["cream"]}"/><rect x="-14" y="-24" width="28" height="16" rx="2" fill="{P["sky"]}"/>') +
    speech(270, 90, P["cream"], flip=True) + plant(60, CF+6, 0.7))
scenes["card-adults"] = svg(CW, CH, P["ochre"],
    chair(150, CF-10, P["cream"], 80) +
    person(150, CF-24, 0.95, SKIN[0], HAIR[3], "bob", P["teal"], P["ink"], "sit_chair", arms="cup",
           extra=f'<rect x="16" y="-56" width="22" height="20" rx="4" fill="{P["yellow"]}"/>') +
    plant(300, CF+6, 0.9) + sun(292, 74, 26, P["yellow"]))

for name, content in scenes.items():
    with open(os.path.join(OUT, f"{name}.svg"), "w") as f:
        f.write(content)
    print("wrote", name)
