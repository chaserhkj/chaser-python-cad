from ocp_vscode import set_port, show_object
import cad_common
from build123d import *
from bd_common import *
from bd_lc import *

from typing import Union, Literal, List, Tuple
import copy
import math
from dataclasses import dataclass, fields

from cad_common import IN

from utils import import_from_file_relative
RackPanel = import_from_file_relative("../Panel.py", "RackPanel")

set_port(3939)

# Parameters
thickness = 1 / 8 * IN
height = 1.75 * IN
front_hole_offset = 5  # without thickness
front_hole_offset += thickness  # from panel bottom
front_hole_offset -= height / 2  # from origin
front_hole_height = 28
front_hole_width = 5.5 * IN
tray_width = 6.5 * IN
tray_depth = 4 * IN
finger_width = 10.0
back_height = 0.5 * IN
width_tolerance = 0.1
thickness_tolerance = 0.1

panel_sk = RackPanel(widthIn=8)
front_hole = Rectangle(front_hole_width, front_hole_height)
front_hole = anchor(front_hole, FRONT)
front_hole = Location((0, front_hole_offset, 0)) * front_hole
panel_sk -= front_hole

builder = LCBuilder(
    default_thickness=thickness,
    default_connect_type=LCConnect.TO_BASE,
    default_joint_config=6,
    auto_thickness_tolerance=thickness_tolerance,
    auto_width_tolerance=width_tolerance)

bottom_sk = Rectangle(tray_width, tray_depth+thickness)
bottom = builder.add_board(bottom_sk)

panel = builder.add_board(Rot(Z=-90)*panel_sk, angle=-90,
                          connect_type=LCConnect.FROM_BASE)

back_sk = Rectangle(tray_width, back_height)
back = builder.add_board(Rot(Z=-90)*back_sk, angle=90, base_board=bottom)

side_sk = Polygon((0, 0), (height-thickness, 0),
                  (back_height, tray_depth), (0, tray_depth))
side_right = builder.add_board(side_sk,
                               base_board=bottom, connect_anchor_modifier=FRONT,
                               joint_config=4)
side_left = builder.add_board(side_sk.mirror(Plane.XZ),
                              base_board=bottom, angle=180, connect_anchor_modifier=BACK,
                              joint_config=4)


side_right_new, panel_new = side_right.join_inplace(panel, 2)
side_left_new, panel_new = side_left.join_inplace(panel_new, 2)
builder.replace_part(side_right, side_right_new)
builder.replace_part(side_left, side_left_new)
builder.replace_part(panel, panel_new)

panel_reinforcement = panel.unjoined_board_synced.moved(
    Pos(Y=-panel.thickness))
builder.add_part(panel_reinforcement)

objs = ("panel_reinforcement", "panel", "bottom",
        "back", "side_left", "side_right")
objs = builder.label_objects(objs, globals())
color_parts_shade(objs)
asmb = builder.make_assembly()
show_object(asmb)
export_assembled_projected_svg(asmb, "output/iFiDACMount_")
