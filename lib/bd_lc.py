from build123d import *
from dataclasses import dataclass, fields
from typing import Union, List, Tuple, Self, Optional, Iterable
from copy import deepcopy, copy
from bd_common import (
    CommonPart, connect_to, anchor_to, bound_loc,
    StraightEdgeJoint, StraightFingerJoint,
    BACK, FRONT, LEFT, RIGHT, TOP, DOWN, CENTER
)
from enum import Enum

# from ocp_vscode import show_object, set_port
# set_port(3939)


class LCConnect(Enum):
    FROM_BASE = 1
    TO_BASE = 2
    FLOAT = 3


@dataclass
class LCJointConfig(object):
    joint: StraightEdgeJoint
    count: int
    distance: Optional[float] = None
    spread: Optional[float] = None


@dataclass
class LCBoard(CommonPart):
    board_sk: Sketch
    thickness: float
    auto_width_tolerance: float = 0
    auto_thickness_tolerance: float = 0

    def make(self):
        self.board_parent = None
        self.board_children = []
        main = extrude(self.board_sk, self.thickness)
        main = BasePartObject(main, align=Align.CENTER)
        main.relocate(Pos())
        self.unjoined_board = main
        return main

    def wrap(self, wrapped: Part):
        new = super().wrap(wrapped)
        new.board_parent = self.board_parent
        new.board_children = self.board_children
        new.unjoined_board = self.unjoined_board
        new.label = self.label
        return new

    @property
    def unjoined_board_synced(self):
        return self.unjoined_board.located(self.location)

    def relocate(self, loc: Location, sync: bool = True):
        """Overridden relocate function to sync-relocate unjoined board
        geometry so that connect works correctly.
        This only needs to be done in relocate, since connect works in LCS.
        Set sync=False when main LCS is not changed, e.g. when merely updating
        location values after a join and wrap"""
        if sync:
            self.unjoined_board.locate(self.location)
            self.unjoined_board.relocate(loc)
        super().relocate(loc)

    def _config_joint(self, other: Self,
                      connect_type: LCConnect,
                      joint_config: Union[LCJointConfig, int],
                      auto_length: Optional[float] = None):
        # Configure joint to use
        joint = None
        if isinstance(joint_config, LCJointConfig):
            joint = joint_config.joint
            joint_count = joint_config.count
            joint_distance = joint_config.distance
            joint_spread = joint_config.spread
            if joint_distance == None and joint_spread == None:
                joint_spread = auto_length
        if isinstance(joint_config, int) and joint_config > 0:
            width = auto_length/(joint_config * 2)
            if connect_type == LCConnect.FROM_BASE:
                joint = StraightFingerJoint(width, self.thickness, other.thickness,
                                            self.auto_width_tolerance, self.auto_thickness_tolerance)
            elif connect_type == LCConnect.TO_BASE:
                joint = StraightFingerJoint(width, other.thickness, self.thickness,
                                            self.auto_width_tolerance, self.auto_thickness_tolerance)
            else:
                raise ValueError
            joint_count = joint_config
            joint_distance = None
            joint_spread = auto_length
        if joint:
            return (joint, joint_count, joint_distance, joint_spread)

    def join_inplace(self, other: Self,
                     joint_config: Union[LCJointConfig, int],
                     connect_by_unjoined_geometry: bool = True):
        # Determine face to join
        face_to_join = min(((f.distance(other), f)
                           for f in self.faces()), key=lambda x: x[0])[1]
        face_normal = face_to_join.normal_at(face_to_join.center())
        joint_direction = Axis((0, 0, 0), face_normal.cross(
            self.location.z_axis.direction))
        # Determine auto_length, by orienting the two parts to Z and comparing
        # Z bounding box sizes
        if connect_by_unjoined_geometry:
            base = self.unjoined_board_synced
            target = other.unjoined_board_synced
        else:
            base = copy(self)
            target = copy(other)
        base.move(joint_direction.location)
        target.move(joint_direction.location)
        auto_length = min(base.bounding_box().size.Z,
                          target.bounding_box().size.Z)

        joint, joint_count, joint_distance, joint_spread = \
            self._config_joint(other, LCConnect.FROM_BASE,
                               joint_config, auto_length)

        new_base, new_target = joint.join(self, other,
                                          Plane(
                                              face_to_join, x_dir=joint_direction.direction),
                                          joint_count, joint_distance, joint_spread)
        new_base = self.wrap(new_base)
        new_base.relocate(self.location, sync=False)
        new_target = other.wrap(new_target)
        new_target.relocate(other.location, sync=False)
        return new_base, new_target

    def connect(self, other: Self, angle: float = 0,
                offset: Tuple[float, float, float] = (0, 0, 0), flip: bool = False,
                connect_type: LCConnect = LCConnect.FLOAT,
                joint_config: Union[LCJointConfig, int, None] = None,
                connect_by_unjoined_geometry: bool = True,
                connect_anchor_modifier: Union[Vector, Tuple[Vector, Vector]] = CENTER):
        # TODO: comment me
        if isinstance(connect_anchor_modifier, Vector):
            connect_anchor_modifier = (connect_anchor_modifier,)*2

        if connect_by_unjoined_geometry:
            base = self.unjoined_board
            target = other.unjoined_board
        else:
            base = self
            target = other
        base = base.located(Rot(Z=-angle))
        if flip:
            base = Rot(X=180) * base
        target = target.located(Rot(Y=-90))
        if connect_type == LCConnect.FROM_BASE:
            from_v = LEFT+DOWN
            to_v = RIGHT+DOWN
        elif connect_type == LCConnect.TO_BASE:
            from_v = RIGHT+DOWN
            to_v = RIGHT+TOP
        elif connect_type == LCConnect.FLOAT:
            from_v = LEFT+DOWN
            to_v = RIGHT+TOP
        else:
            raise ValueError
        from_v += connect_anchor_modifier[0]
        to_v += connect_anchor_modifier[1]
        target = connect_to(target, base, from_v, to_v)
        target = Location(offset) * target
        auto_length = min(base.bounding_box().size.Y,
                          target.bounding_box().size.Y)
        joint, joint_count, joint_distance, joint_spread = \
            self._config_joint(other, connect_type, joint_config, auto_length)
        base_to_join = self.located(base.location)
        target_to_join = other.located(target.location)
        if joint:
            if connect_type == LCConnect.FROM_BASE:
                base_joined, target_joined = joint.join(base_to_join, target_to_join,
                                                        Plane(base.faces().sort_by(
                                                            Axis.X).last, x_dir=(0, 1, 0)),
                                                        joint_count, joint_distance, joint_spread)
                base_joined = self.wrap(base_joined)
                target_joined = other.wrap(target_joined)
            elif connect_type == LCConnect.TO_BASE:
                target_joined, base_joined = joint.join(target_to_join, base_to_join,
                                                        Plane(target.faces().sort_by(
                                                            Axis.Z).first, x_dir=(0, 1, 0)),
                                                        joint_count, joint_distance, joint_spread)
                base_joined = self.wrap(base_joined)
                target_joined = other.wrap(target_joined)
            else:
                raise ValueError
        if connect_type == LCConnect.FLOAT:
            base_joined = base_to_join
            target_joined = target_to_join
        # From base.location to base_joined, LCS is not changed
        # We are only updating location values after they are lost in join
        base_joined.relocate(base.location, sync=False)
        target_joined.relocate(target.location, sync=False)
        target_joined.move(self.location*base.location.inverse())
        base_joined.locate(self.location)
        target_joined.board_parent = base_joined
        base_joined.board_children.append(target_joined)
        return base_joined, target_joined


@dataclass
class LCBuilder(object):
    default_thickness: float = 3
    default_joint_config: LCJointConfig = 3
    default_connect_type: LCConnect = LCConnect.FLOAT
    auto_width_tolerance: float = 0
    auto_thickness_tolerance: float = 0

    def __post_init__(self):
        self._parts = []
        self._current_board = None

    @property
    def current_board(self):
        return self._parts[self._current_board]

    @current_board.setter
    def current_board(self, b):
        self._current_board = b.builder_idx

    def add_board(self, sk: Sketch, thickness: Optional[float] = None, angle: float = 0,
                  offset: Tuple[float, float, float] = (0, 0, 0), flip: bool = False,
                  connect_type: Optional[LCConnect] = None,
                  joint_config: Union[LCJointConfig, int, None] = None,
                  base_board: Optional[LCBoard] = None, **kwargs):
        # TODO: comment me
        if not connect_type:
            connect_type = self.default_connect_type
        if connect_type != LCConnect.FLOAT and joint_config == None:
            joint_config = self.default_joint_config
        if base_board:
            self.current_board = base_board

        target = LCBoard(
            board_sk=sk,
            thickness=thickness if thickness != None else self.default_thickness,
            auto_width_tolerance=self.auto_width_tolerance,
            auto_thickness_tolerance=self.auto_thickness_tolerance)

        if not self._parts:
            target.builder_idx = 0
            self.current_board = target
            self._parts.append(target)
            return target

        base, target = self.current_board.connect(target,
                                                  angle=angle, offset=offset, flip=flip,
                                                  connect_type=connect_type, joint_config=joint_config, **kwargs)
        self.replace_part(self.current_board, base)

        target.builder_idx = len(self._parts)
        self.current_board = target
        self._parts.append(target)
        return target

    def add_part(self, target: Part):
        """Add a non-board part"""
        if not self._parts:
            target.builder_idx = 0
            self._parts.append(target)
            return
        target.builder_idx = len(self._parts)
        self._parts.append(target)

    def replace_part(self, ref: Part, new: Part):
        idx = ref.builder_idx
        new.builder_idx = idx
        self._parts[idx] = new

    def label_objects(self, names: Iterable[str], scope: dict):
        """Label objects by matching builder_idx"""
        objs = []
        for n in names:
            idx = scope[n].builder_idx
            obj = self._parts[idx]
            obj.label = n
            objs.append(obj)
        return objs

    def make_assembly(self, **kwargs):
        return Compound(children=self._parts, **kwargs)


def test():
    builder = LCBuilder(default_connect_type=LCConnect.FROM_BASE)
    b1 = builder.add_board(Rectangle(20, 30))
    b2 = builder.add_board(Rectangle(40, 30), angle=180, flip=True)
    b3 = builder.add_board(Rectangle(10, 30), offset=(0, 0, -5))
    b4 = builder.add_board(Rectangle(30, 20), angle=270, offset=(-10,
                           0, 0), connect_type=LCConnect.TO_BASE, base_board=b1)
    return builder.make_assembly()
