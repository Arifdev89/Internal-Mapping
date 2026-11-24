"""
Sample hospital used by `python manage.py seed_map`.

This file is plain Python (no Django imports) so the map can be inspected
and tested on its own.

Coordinates are SVG units on a 1000 x 600 canvas. One unit = 0.1 metre,
so the main corridor is about 78 metres long. Every floor uses the same
layout for stairs and lifts so floors line up when you switch between them.

            top rooms  (y 80..250)
   ENT ===== main corridor y=300 ====== J2 ===== J1
            bottom rooms (y 350..520)           |  (vertical corridor x=840)
                                              STAIR
                                                |
                                              LIFT
"""
import math

METERS_PER_UNIT = 0.1
SVG_WIDTH = 1000
SVG_HEIGHT = 600

ORGANISATION = {"name": "Demo Health Network", "slug": "demo-health-network"}

BUILDING = {
    "name": "City General Hospital",
    "building_type": "hospital",
    "address": "Sample address (set your own lat/lng with --lat and --lng)",
}

FLOORS = [(0, "Ground Floor"), (1, "First Floor"), (2, "Second Floor")]

PREFIX = {0: "G", 1: "F1", 2: "F2"}

# Fixed positions shared by every floor.
J1_XY = (840, 300)       # east junction: main corridor meets the vertical corridor
J2_XY = (700, 300)       # service junction
STAIR_XY = (840, 360)
LIFT_XY = (840, 450)
SLIFT_XY = (700, 400)    # staff-only service lift


def _place(level, name, category, description, rect, code, node_xy,
           node_type="room", restricted=False):
    return {
        "level": level,
        "name": name,
        "category": category,
        "description": description,
        "rect": rect,          # x, y, width, height on the SVG map
        "code": code,          # code of the navigation node at the door
        "node_xy": node_xy,
        "node_type": node_type,
        "restricted": restricted,
    }


PLACES = [
    # ---------------- Ground floor ----------------
    _place(0, "Main Entrance", "entrance", "Main hospital entrance",
           (10, 260, 50, 80), "G-ENT", (60, 300), "entrance"),
    _place(0, "Reception", "facility", "Enquiries and registration",
           (120, 80, 160, 170), "G-REC", (200, 300)),
    _place(0, "Emergency Ward", "ward", "24x7 emergency care",
           (300, 80, 240, 170), "G-EMG", (420, 300)),
    _place(0, "Pharmacy", "facility", "Medicines and prescriptions",
           (560, 80, 160, 170), "G-PHA", (640, 300)),
    _place(0, "Laboratory", "facility", "Blood tests and sample collection",
           (220, 350, 220, 170), "G-LAB", (330, 300)),
    # ---------------- First floor ----------------
    _place(1, "General Medicine", "department", "General physicians",
           (120, 80, 160, 170), "F1-GEN", (200, 300)),
    _place(1, "Cardiology", "department", "Heart and blood vessel care",
           (300, 80, 240, 170), "F1-CAR", (420, 300)),
    _place(1, "Neurology", "department", "Brain and nerve care",
           (560, 80, 160, 170), "F1-NEU", (640, 300)),
    _place(1, "Waiting Area", "facility", "Seating area for visitors",
           (220, 350, 220, 170), "F1-WAIT", (330, 300)),
    # ---------------- Second floor ----------------
    _place(2, "Orthopaedics", "department", "Bones and joints",
           (120, 80, 160, 170), "F2-ORT", (200, 300)),
    _place(2, "Radiology", "department", "X-ray, CT and MRI",
           (300, 80, 240, 170), "F2-RAD", (420, 300)),
    _place(2, "Operation Theatre", "ward", "Surgery. Permission needed.",
           (560, 80, 160, 170), "F2-OT", (640, 300), restricted=True),
    _place(2, "ICU", "ward", "Intensive care. Permission needed.",
           (220, 350, 220, 170), "F2-ICU", (330, 300), restricted=True),
]

# Stairs, lift and service lift exist on every floor.
for _level, _p in PREFIX.items():
    PLACES.append(_place(_level, "Staircase", "transport", "Stairs to other floors",
                         (880, 330, 70, 60), f"{_p}-STAIR", STAIR_XY, "staircase"))
    PLACES.append(_place(_level, "Lift", "transport", "Wheelchair accessible lift",
                         (880, 420, 70, 60), f"{_p}-LIFT", LIFT_XY, "lift"))
    PLACES.append(_place(_level, "Service Lift (Staff Only)", "service", "Staff only",
                         (660, 415, 80, 60), f"{_p}-SLIFT", SLIFT_XY, "lift",
                         restricted=True))

# Corridor order along the main corridor, west to east, for every floor.
CORRIDOR_CHAINS = {
    0: ["G-ENT", "G-REC", "G-LAB", "G-EMG", "G-PHA", "G-J2", "G-J1"],
    1: ["F1-GEN", "F1-WAIT", "F1-CAR", "F1-NEU", "F1-J2", "F1-J1"],
    2: ["F2-ORT", "F2-ICU", "F2-RAD", "F2-OT", "F2-J2", "F2-J1"],
}


def _build_nodes():
    nodes = []
    for place in PLACES:
        nodes.append({
            "code": place["code"],
            "name": place["name"],
            "level": place["level"],
            "x": place["node_xy"][0],
            "y": place["node_xy"][1],
            "node_type": place["node_type"],
        })
    for level, p in PREFIX.items():
        nodes.append({"code": f"{p}-J1", "name": "East Junction", "level": level,
                      "x": J1_XY[0], "y": J1_XY[1], "node_type": "junction"})
        nodes.append({"code": f"{p}-J2", "name": "Service Junction", "level": level,
                      "x": J2_XY[0], "y": J2_XY[1], "node_type": "junction"})
    return nodes


NODES = _build_nodes()
_NODE_BY_CODE = {n["code"]: n for n in NODES}


def _distance(code_a, code_b):
    a, b = _NODE_BY_CODE[code_a], _NODE_BY_CODE[code_b]
    return round(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) * METERS_PER_UNIT, 1)


def _edge(a, b, distance=None, connection_type="corridor", accessible=True,
          restricted=False):
    return {
        "from": a,
        "to": b,
        "distance": distance if distance is not None else _distance(a, b),
        "connection_type": connection_type,
        "accessible": accessible,
        "restricted": restricted,
    }


def _build_edges():
    edges = []
    # Walking edges inside each floor.
    for level, chain in CORRIDOR_CHAINS.items():
        p = PREFIX[level]
        for a, b in zip(chain, chain[1:]):
            edges.append(_edge(a, b))
        edges.append(_edge(f"{p}-J1", f"{p}-STAIR"))
        edges.append(_edge(f"{p}-STAIR", f"{p}-LIFT"))
        edges.append(_edge(f"{p}-J2", f"{p}-SLIFT", restricted=True))
    # Edges between floors.
    for lower, upper in [(0, 1), (1, 2)]:
        lo, up = PREFIX[lower], PREFIX[upper]
        edges.append(_edge(f"{lo}-LIFT", f"{up}-LIFT", 6.0, "elevator", True))
        edges.append(_edge(f"{lo}-STAIR", f"{up}-STAIR", 10.0, "stairs", False))
        edges.append(_edge(f"{lo}-SLIFT", f"{up}-SLIFT", 5.0, "elevator", True, True))
    return edges


EDGES = _build_edges()

# Offsets are added to the --lat/--lng you pass to seed_map.
ENTRANCES = [
    {"name": "Main Entrance", "node": "G-ENT", "dlat": 0.0, "dlng": 0.0, "is_main": True},
    {"name": "Emergency Entrance", "node": "G-EMG", "dlat": 0.00015, "dlng": 0.00012,
     "is_main": False},
]

QR_CODES = [
    ("QR-ENTRANCE", "Main Entrance", "G-ENT"),
    ("QR-RECEPTION", "Reception desk", "G-REC"),
    ("QR-G-STAIRS", "Ground floor stairs", "G-STAIR"),
    ("QR-G-LIFT", "Ground floor lift", "G-LIFT"),
    ("QR-F1-STAIRS", "First floor stairs", "F1-STAIR"),
    ("QR-F1-LIFT", "First floor lift", "F1-LIFT"),
    ("QR-F1-WAITING", "First floor waiting area", "F1-WAIT"),
    ("QR-F2-STAIRS", "Second floor stairs", "F2-STAIR"),
    ("QR-F2-LIFT", "Second floor lift", "F2-LIFT"),
    ("QR-F2-RADIOLOGY", "Radiology door", "F2-RAD"),
]

BEACON_UUID = "f7826da6-4fa2-4e98-8024-bc5b71e0893e"

# (label, major, minor, node code)
BEACONS = [
    ("Entrance beacon", 1, 1, "G-ENT"),
    ("Ground lift beacon", 1, 2, "G-LIFT"),
    ("First floor lift beacon", 1, 3, "F1-LIFT"),
    ("Second floor lift beacon", 1, 4, "F2-LIFT"),
]
