import cad_common
from build123d import *
from build123d import Shape
from build123d import exporters3d
from dataclasses import dataclass, fields, _MISSING_TYPE, field
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from typing import (
    Union, List, Optional, Type, Callable, Tuple, Dict, Any)
from enum import Enum
from copy import copy
import os, sys
import math
import colorsys

_layer_height = 0.2


def layer_height():
    return _layer_height


def set_layer_height(h):
    global _layer_height
    _layer_height = h


_line_width = 0.4


def line_width():
    return _line_width


def set_line_width(w):
    global _line_width
    _line_width = w


# Origin
O = Vector(0, 0, 0)
CENTER = O
BACK = Vector(0, 1, 0)
FWD = Vector(0, -1, 0)
FRONT = FWD
TOP = Vector(0, 0, 1)
UP = TOP
BOT = Vector(0, 0, -1)
DOWN = BOT
LEFT = Vector(-1, 0, 0)
RIGHT = Vector(1, 0, 0)


def anchor(shape, anchor_vector: Vector, keep_lcs: bool = True):
    result = shape.moved(anchor_loc(shape, anchor_vector))
    if not keep_lcs:
        result.relocate(shape.location)
    return result


def anchor_loc(shape, anchor_vector: Vector):
    return bound_loc(shape, anchor_vector).inverse()


def min_max_to_bounds(min_vec, max_vec):
    return ((min_vec.X, max_vec.X),
            (min_vec.Y, max_vec.Y),
            (min_vec.Z, max_vec.Z))


def bound_loc(bb, bound_vector: Vector):
    if isinstance(bb, Shape):
        bb = bb.bounding_box()
    if isinstance(bb, BoundBox):
        bb = (bb.min, bb.max)
    if isinstance(bb, tuple) and isinstance(bb[0], Vector):
        bb = min_max_to_bounds(*bb)

    def _calc_coord(direction, bounds):
        if direction > 0:
            return bounds[1]
        elif direction == 0:
            return (bounds[0] + bounds[1])/2
        elif direction < 0:
            return bounds[0]
        else:
            raise ValueError
    bound_vec = tuple(_calc_coord(d, b) for d, b in zip(bound_vector, bb))
    return Pos(*bound_vec)


def anchor_to(shape, target_loc, anchor_vec, keep_lcs: bool = True):
    anchored = anchor(shape, anchor_vec, keep_lcs)
    anchored.move(target_loc)
    return anchored


def connect_to(shape, target, from_vec, to_vec, keep_lcs: bool = True):
    return anchor_to(shape, bound_loc(target, to_vec), from_vec, keep_lcs)

def connect_relatively_to(shape, target, from_vec, to_vec, keep_lcs: bool = True):
    return target.location*anchor_to(shape, bound_loc(target.located(Pos()), to_vec), from_vec, keep_lcs)

def _get_field_default(f):
    if not isinstance(f.default, _MISSING_TYPE):
        return f.default
    if not isinstance(f.default_factory, _MISSING_TYPE):
        return f.default_factory()
    raise Exception(f"No default and no default_factory for field {f.name}")

def init_dataclass_from(data_class, obj, param_name_remap={}, *args, **kwargs):
    '''Initialize dataclass from an exiting dataclass object
    With remaps and overriding arguments as well'''
    fields_set = set(f.name for f in fields(data_class))
    param_dict = dict((param_name_remap.get(k, k), getattr(obj, k)) for k in dir(obj)
                if k in fields_set
                )
    param_dict.update(dict((param_name_remap[k], getattr(obj, k)) for k in param_name_remap))
    param_dict.update(kwargs)
    return data_class(*args, **param_dict)

def rdeq(op1, op2, ndigits=3):
    '''Helper for doing rounded equal checks'''
    return round(op1, ndigits) == round(op2, ndigits)


class CommonCLI(object):
    def __init__(self,
                 obj_class: Type,
                 extra_arg_config: dict = {},
                 parser: ArgumentParser = ArgumentParser(
                     formatter_class=ArgumentDefaultsHelpFormatter,
                     conflict_handler='resolve'),
                 args: List[Any] = [],
                 override_conflict_args: bool = False,
                 ):
        self._obj = None
        self._obj_class = obj_class
        self._parser = parser
        self._unparsed_args = args

        def get_aliases(name): return extra_arg_config.get(
            name, {}).get("aliases", [])

        def get_extra(name): return {
            k: extra_arg_config[k] for k in extra_arg_config.get(name, {}) if k != "aliases"}

        for f in fields(self._obj_class):
            if f.metadata.get("no_CLI"):
                continue
            aliases = get_aliases(f.name)
            extra = copy(get_extra(f.name))
            if isinstance(f.default, _MISSING_TYPE) and \
                isinstance(f.default_factory, _MISSING_TYPE):
                self._parser.add_argument(f.name, type=f.type, *aliases, **extra)
            else:
                if not "default" in extra:
                    extra["default"] = _get_field_default(f)
                if not "help" in extra:
                    extra["help"] = f.name
                self._parser.add_argument(f"--{f.name}", type=f.type, *aliases, **extra)

        self.add_output_argument()
    
    def add_output_argument(self):
        self._parser.add_argument(
            "-o", "--output", help="Output file to write to, if omitted, output will be disabled")

    def parse_args(self, extra_args: Optional[List[Any]] = None):
        _args = self._parser.parse_args(self._unparsed_args + extra_args)
        return _args
    
    def _get_init_args(self):
        init_args = {f.name: getattr(self._args, (f.name)) for f in fields(
            self._obj_class) if f.name in self._args}
        init_non_args = {f.name: _get_field_default(f) for f in fields(
            self._obj_class) if not f.name in self._args}
        init_args.update(init_non_args)
        return init_args

    def make(self):
        if self._obj is None:
            self._obj = self._obj_class(**self._get_init_args())
        return self._obj
    
    def remake_with_args(self, args):
        _args = self.parse_args(args)
        if hasattr(self, "_args") and _args == self._args:
            return self.make()
        self._args = _args

        self.clear_cached()
        return self.make()

    # Clear cached object to force remake
    def clear_cached(self):
        self._obj = None

    def save_output(self):
        raise NotImplemented

    @property
    def output_is_set(self):
        return not self._args.output is None

    def main(self):
        self.clear_cached()

        self._args = self.parse_args(sys.argv[1:])
        if self.output_is_set:
            self.save_output()
    
@dataclass(kw_only=True)
class CommonPart(BasePartObject):
    rotation: RotationLike = (0, 0, 0)
    align: Union[Align, tuple[Align, Align, Align]] = None
    mode: Mode = Mode.SUBTRACT
    main_part: Optional[Part] = None

    def make(self) -> Part:
        raise NotImplementedError
    
    def init_params(self):
        '''Override this method in subclasses to initialize
        all indirect parameters'''
        return

    def __post_init__(self):
        self.init_params()
        self._make()
        super().__init__(self.main_part, rotation=self.rotation,
                         align=self.align, mode=self.mode)
    
    def _make(self):
        if not self.main_part:
            self.main_part = self.make()

    def wrap(self, wrapped: Part):
        param = dict((f.name, getattr(self, f.name))
                     for f in fields(self.__class__))
        param["main_part"] = wrapped
        new = self.__class__(**param)
        return new

@dataclass(kw_only=True)
class CommonJoinedPart(CommonPart):
    '''A Part that is defined by joining multiple subparts.
    Each subpart will define a positive and a negative component
    The final part is built by union of positives minus union of negatives'''
    positive_parts: List[Part] = field(default_factory=list, metadata={"no_CLI": True})
    negative_parts: List[Part] = field(default_factory=list, metadata={"no_CLI": True})
    
    def make(self) -> Tuple[List[Part], List[Part]]:
        raise NotImplementedError

    def _make(self):
        if not self.positive_parts and not self.negative_parts:
            self.positive_parts, self.negative_parts = self.make()
        if not self.main_part:
            self.main_part = Part() + self.positive_parts - self.negative_parts
            self.post_process()
    
    def post_process(self):
        '''Post processing after joining, override in subclasses'''

class CommonPartCLI(CommonCLI):
    def save_output(self):
        ext = os.path.splitext(self._args.output)[1][1:]
        if not hasattr(exporters3d, f"export_{ext}"):
            raise ValueError("Unknown output file type")
        export_func = getattr(exporters3d, f"export_{ext}")
        export_func(self.make(), self._args.output)

@dataclass(kw_only=True)
class CommonSketch(BaseSketchObject):
    rotation: RotationLike = (0, 0, 0)
    align: Union[Align, tuple[Align, Align, Align]] = None
    mode: Mode = Mode.SUBTRACT
    main_sketch: Optional[Sketch] = None

    def make(self):
        raise NotImplementedError

    def init_params(self):
        '''Override this method in subclasses to initialize
        all indirect parameters'''
        return

    def __post_init__(self):
        self.init_params()
        self._make()
        super().__init__(self.main_sketch, rotation=self.rotation,
                         align=self.align, mode=self.mode)

    def _make(self):
        if not self.main_sketch:
            self.main_sketch = self.make()

    def wrap(self, wrapped: Sketch):
        param = dict(getattr(self, f.name) for f in fields(self.__class__))
        param["main_sketch"] = wrapped
        new = self.__class__(**param)
        return new

@dataclass(kw_only=True)
class CommonAssembly(Compound):
    # List of (children, <individual_save_name> or
    #           <None for not saving individually>)
    children_specs: List[Tuple[Shape, Optional[str]]] = field(default_factory=list, metadata={"no_CLI": True})
    compound_args: Dict[str, Any] = field(default_factory=dict, metadata={"no_CLI": True})
    # Custom save function to be called when saving
    # custom_save_func(compound_to_save, save_path_prefix)
    custom_save_func: Optional[Callable[[Compound, str], None]] = field(default=None, metadata={"no_CLI": True})

    def make(self):
        raise NotImplementedError
    
    def init_params(self):
        '''Override this method in subclasses to initialize
        all indirect parameters'''
        return

    def __post_init__(self):
        self.init_params()
        self._make()
        children = [(copy(m), n) for m, n in self.children_specs]
        for m, n in children:
            m.label = n
        children = [m for m, n in children]
        super().__init__(children=children, **self.compound_args)
    
    def _make(self):
        if not self.children_specs:
            self.children_specs = self.make()



class CommonAssemblyCLI(CommonCLI):
    def add_output_argument(self):
        self._parser.add_argument(
            "-o", "--output_prefix",
            help="Output filename prefixes to write to, if omitted, output will be disabled")
        self._parser.add_argument(
            "-t", "--output_types",
            choices=["stl", "step", "combined_step"],
            default="stl",
            help="Type of output files to write")
        self._parser.add_argument(
            "-C", "--no_custom_saves",
            default=False, action="store_true",
            help="Disable custom saves as defined by children assemblies")
    @property
    def output_is_set(self):
        return not self._args.output_prefix is None

    def remake_children_with_args(self, args):
        _args = self.parse_args(args)
        if hasattr(self, "_args") and _args == self._args:
            self.make()
            return dict((k, v) for v, k in self._obj.children_specs)
        self._args = _args

        self.clear_cached()
        self.make()
        return dict((k, v) for v, k in self._obj.children_specs)

    def save_output(self):
        out_type = self._args.output_types
        if not self._args.no_custom_saves:
            for (obj, name) in self.make().children_specs:
                if hasattr(obj, "custom_save_func") and not (obj.custom_save_func is None):
                    obj.custom_save_func(obj, f"{self._args.output_prefix}_{name}")
        if out_type == "combined_step":
            exporters3d.export_step(self.make(), f"{self._args.output_prefix}.step")
        else:
            if not hasattr(exporters3d, f"export_{out_type}"):
                raise ValueError("Unknown output file type")
            export_func = getattr(exporters3d, f"export_{out_type}")
            for (obj, name) in self.make().children_specs:
                if name is None:
                    continue
                export_func(obj,
                    f"{self._args.output_prefix}_{name}.{out_type}")

class NutTrapType(Enum):
    SIDE = 1
    INLINE = 2

@dataclass
class NutTrap(CommonPart):
    spec: str = "m3"
    width: float = 10.0
    trap_type: NutTrapType = NutTrapType.SIDE
    tolerance: float = 0.15
    floating_mask: bool = True

    def make(self):
        if not self.spec in cad_common.nut:
            raise NotImplementedError
        self.r = cad_common.nut.get(self.spec).d / 2 + self.tolerance
        self.h = cad_common.nut.get(self.spec).h + 2 * self.tolerance
        nut_cross = RegularPolygon(self.r, 6)
        nut = extrude(nut_cross, self.h)
        if self.trap_type == NutTrapType.SIDE:
            cut_d = max(self.r * 2, self.h)
            cutter = Plane.YZ * Rectangle(cut_d, cut_d)
            trap_cross = nut & cutter
            trap = nut + extrude(trap_cross, self.width)
        elif self.trap_type == NutTrapType.INLINE:
            trap = nut
        if self.floating_mask:
            mask = FloatingHoleBridgeMask(
                nut_cross,
                Plane(nut.faces().sort_by(Axis.Z).last) *
                Circle(self.r / 2))
            trap += mask
        trap = Location([0, 0, -self.h / 2]) * trap
        return trap

@dataclass
class FloatingHoleBridgeMask(CommonPart):
    bot_sketch: Sketch
    top_sketch: Sketch

    def make(self):
        bot_bb = self.bot_sketch.bounding_box()
        top_bb = self.top_sketch.bounding_box()

        first_mask = Rectangle(
            top_bb.size.X + line_width() * 2,
            bot_bb.size.Y + line_width() * 2)
        first_mask = self.bot_sketch & first_mask
        first_mask = Plane(top_bb.center()) * first_mask
        first_mask = extrude(first_mask, layer_height())
        second_mask = Rectangle(
            top_bb.size.X + line_width() * 2,
            top_bb.size.Y + line_width() * 2)
        second_mask = Plane(top_bb.center()) * second_mask
        second_mask = extrude(second_mask, layer_height() * 2)

        return first_mask + second_mask


def lay_cut_board(board_part: Part):
    """Lay down a board on XY Plane, aligning center to origin and
    rotating the shortest bounding box direction of the part towards
    the Z Axis"""
    b = board_part.bounding_box()
    axis_to_rot, _ = min((
        ("Y", b.size.X), ("X", b.size.Y), (None, b.size.Z)),
        key=lambda x: x[1])
    part = anchor(board_part, CENTER)
    if axis_to_rot:
        part = Rotation(**{axis_to_rot: 90}) * part
    return part


def section_board(board_part: Part):
    """Section a board to get 2D layout, keeps labels from input"""
    laid = lay_cut_board(board_part)
    sk = section(laid, Plane.XY)
    sk.label = board_part.label
    return sk


def color_parts(part_list: List[Part], hsv):
    """Color part list with different colors
    hsv is a tuple of tuples:
        ((h_start, h_end), (s_start, s_end), (v_start, v_end))
    means the start and end values for each part along the list
    or alternatively, a single value means using this value for
    the entire list"""
    def expand(val):
        l = len(part_list)
        if isinstance(val, float):
            return (val, )*l
        elif isinstance(val, tuple) and len(val) == 2:
            diff = (val[1]-val[0])/l
            return tuple(val[0] + diff * i for i in range(l))
        else:
            raise ValueError
    hsv_vals = tuple(
        expand(val)
        for val in hsv
    )
    hsv_vals = zip(*hsv_vals)
    for p, color_vals in zip(part_list, hsv_vals):
        p.color = Color(*colorsys.hsv_to_rgb(*color_vals))


def color_parts_shade(part_list, hue=0.12, sat_bnd=0.4, val_bnd=0.7):
    """Color part list with different shades of the same hue"""
    l1 = int(len(part_list) / 2)
    l2 = len(part_list) - l1
    val_diff = (1 - val_bnd)/l1
    sat_diff = (1 - sat_bnd)/l2
    colors_1 = [(hue, 1.0, val_bnd + i*val_diff) for i in range(l1)]
    colors_2 = [(hue, 1.0 - i*sat_diff, 1.0) for i in range(l2)]
    for p, color in zip(part_list, colors_1 + colors_2):
        p.color = Color(*colorsys.hsv_to_rgb(*color))


def save_dxf(cut, fn):
    exporter = ExportDXF(unit=Unit.MM, line_weight=0.5)
    exporter.add_layer("Layer 1")
    exporter.add_shape(cut, layer="Layer 1")
    exporter.write(fn)


def save_svg(cut, fn):
    exporter = ExportSVG(unit=Unit.MM, line_weight=0.5)
    exporter.add_layer("Layer 1")
    exporter.add_shape(cut, layer="Layer 1")
    exporter.write(fn)


def save_stl(part: Part, fn):
    part.export_stl(fn)


def export_assembled_projected_svg(assembly: Compound, prefix: str):
    children = map(section_board, assembly.children)
    for child in children:
        save_svg(child, f"{prefix}{child.label}.svg")


def label_objects(object_names: List[str], source):
    objs = []
    for n in object_names:
        source[n].label = n
        objs.append(source[n])
    return objs


@dataclass
class StraightEdgeJoint(CommonPart):
    """A joint for joining two parts together along a straight edge
    Contains: A positive part to add to the male side. A negative part
    to subtract from the female side, and an optional receptacle part
    to add to the female side after subtraction
    Args:
        length: length of the joint into the female side
        width: width of the joint along the edge
        thickness: thickness of the joint against the edge"""
    length: float
    width: float
    thickness: float

    def make(self):
        """Make all parts for the joint, returns the positive part"""
        raise NotImplemented

    def get_negative(self):
        """Returns the made negative part of the joint"""
        raise NotImplemented

    def get_receptacle(self):
        """Returns the made receptacle part of the joint.
        Returning None means no receptacle to be added"""
        return None

    def join(self, male, female, plane, count, distance=None, spread=None):
        if distance is None:
            distance = spread/count
        m_part = male + \
            [plane * loc * self for loc in
                GridLocations(distance, 0, count, 1)]
        f_part = female - \
            [plane * loc * self.get_negative() for loc in
                GridLocations(distance, 0, count, 1)]
        rec = self.get_receptacle()
        if rec != None:
            f_part += [plane * loc * self.get_receptacle() for loc in
                       GridLocations(distance, 0, count, 1)]
        return (m_part, f_part)


class StraightFingerJoint(StraightEdgeJoint):
    def __init__(self, width, thickness_from, thickness_to=None, width_tolerance=0, thickness_tolerance=0, **others):
        self.width_tolerance = width_tolerance
        self.thickness_tolerance = thickness_tolerance
        if thickness_to == None:
            thickness_to = thickness_from
        super().__init__(length=thickness_to, width=width, thickness=thickness_from, **others)

    def make(self):
        b = Box(self.width, self.thickness,
                self.length-self.thickness_tolerance)
        return anchor(b, BOT)

    def get_negative(self):
        b = Box(self.width+self.width_tolerance*2, self.thickness +
                self.thickness_tolerance*2, self.length+self.thickness_tolerance)
        return anchor(b, BOT)
