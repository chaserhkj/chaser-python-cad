import cad_common
from build123d import *
from bd_common import *

from typing import Union, Literal, List, Tuple
import copy
import math
from dataclasses import dataclass, fields

from cad_common import IN

@dataclass(kw_only=True)
class RackPanel(CommonSketch):
    widthIn: float = 19
    heightU: int = 1
    uHeightIn: float = 1.75
    holeYDistIn: float = 0.625
    railWidthIn: float = 0.625
    heightTolerance: float = 0
    holeD: float = 6
    holeW: float = 3.5
    filletR: float = 2

    @property
    def width(self):
        return self.widthIn*IN

    @property
    def height(self):
        return self.heightU*self.uHeightIn*IN

    def make(self):
        main = Rectangle(self.width, self.height - 2*self.heightTolerance)
        main = fillet(main.vertices(), self.filletR)
        slot = SlotCenterPoint((0, 0), (self.holeW/2, 0), self.holeD)
        slots1U = Sketch() + [loc *slot for loc in GridLocations((self.widthIn - self.railWidthIn) * IN, 
            2 * self.holeYDistIn * IN, 2, 2)]
        slots = [loc * slots1U for loc in GridLocations(0, self.uHeightIn*IN, 1, self.heightU)]
        main = main - slots
        return main

@dataclass(kw_only=True)
class ModularPanel(CommonSketch):
    heightU: int = 1
    widthU: int = 1
    uHeightIn: float = 1.75
    uWidth: float = 25
    heightTolerance: float = 0
    holeD: float = cad_common.screw.m3.clearance_hole_d.medium
    frameHeight: float = 9
    filletR: float = 2

    @property
    def netHeight():
        return self.heightU*self.uHeightIn*IN - 2 * self.frameHeight

    @property
    def width(self):
        return self.widthU*self.uWidth

    @property
    def height(self):
        return self.heightU*self.uHeightIn*IN
    
    def make(self):
        main = Rectangle(self.width, self.height - 2*self.heightTolerance)
        main = fillet(main.vertices(), self.filletR)
        main -= [loc * Circle(self.holeD/2) for loc in
            GridLocations(self.uWidth, self.height - self.frameHeight,
                self.widthU, 2)]
        return main

if __name__ == "__main__":
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--output", default="output/Panel.svg", help="Output file path")
    subs = parser.add_subparsers(dest="panel_type", help="Type of panel")
    parser_rack = subs.add_parser("rack", help="Rack mount panel")
    for f in fields(RackPanel):
        parser_rack.add_argument(f"--{f.name}", default=f.default, type=f.type, help=f"Value for {f.name}")
    parser_mod = subs.add_parser("modular", help="Modular panel")
    for f in fields(ModularPanel):
        parser_mod.add_argument(f"--{f.name}", default=f.default, type=f.type, help=f"Value for {f.name}")
    args = parser.parse_args()
    if args.panel_type == "rack":
        part_args = dict((f.name, getattr(args, f.name)) for f in fields(RackPanel))
        panel = RackPanel(**part_args)
    elif args.panel_type == "modular":
        part_args = dict((f.name, getattr(args, f.name)) for f in fields(ModularPanel))
        panel = ModularPanel(**part_args)
    exporter = ExportSVG(unit=Unit.MM, line_weight=0.5)
    exporter.add_layer("Layer 1", line_color=(0, 0, 0))
    exporter.add_shape(panel, layer="Layer 1")
    exporter.write(args.output)
