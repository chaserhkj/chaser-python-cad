from box import Box
slop = 0.15
IN = 25.4
screw = Box({
    "m2": {
        "clearance_hole_d": {
            "close": 2.2,
            "medium": 2.4,
            "free": 2.6
        },
        "tap_hole_d": 1.6
    },
    "m3": {
        "clearance_hole_d": {
            "close": 3.2,
            "medium": 3.4,
            "free": 3.6
        },
        "tap_hole_d": 2.5,
        "countersink_d": 6.94
    },
    "m4": {
        "clearance_hole_d": {
            "close": 4.3,
            "medium": 4.5,
            "free": 4.8
        },
        "tap_hole_d": 3.3,
        "countersink_d": 9.18
    },
    "m5": {
        "clearance_hole_d": {
            "close": 5.3,
            "medium": 5.5,
            "free": 5.8
        },
        "tap_hole_d": 4.2,
        "countersink_d": 11.47
    },
    "m6": {
        "clearance_hole_d": {
            "close": 6.4,
            "medium": 6.6,
            "free": 7
        },
        "tap_hole_d": 5,
        "countersink_d": 13.71
    },
    "countersink_angle": 90
})
nut = Box({
    "m2": {
        "d": 4.62,
        "h": 1.60
    },
    "m3": {
        "d": 6.35,
        "h": 2.40
    },
    "m4": {
        "d": 8.08,
        "h": 3.2
    },
    "m5": {
        "d": 9.24,
        "h": 4.7
    }
})
ball_bearing = Box({
    "608-2rs": {
        "od": 22.0,
        "id": 8.0,
        "depth": 7.0
    }
})
thrust_bearing = Box({
    "51101": {
        "od": 26.0,
        "id": 12.0,
        "depth": 9.0
    }
})
breadboard_pcb = Box({
    "wide": {
        "width": 40.0,
        "length": 60.0,
        "hole_margin_w": 1.5,
        "hole_margin_l": 1.5,
        "hole_d": 2.2
    }
})