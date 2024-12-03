# 3D printed snap clip for board-like objects

import cad_common
from build123d import *
from bd_common import *
import math

from dataclasses import dataclass

@dataclass(kw_only=True)
class BoardSnapClip(CommonPart):
    length: float = 10
    depth: float = 1
    snap_tolerance: float = 0
    def init_params(self):
        self.width = math.sqrt(2)*self.depth
        self.full_length = self.length + 2*self.depth
    def make(self):
        sk = Polygon((0, 0), (0, -self.depth), (self.depth, -self.depth), align=None)
        main = extrude(sk, self.length)
        main = Rot(X=90) * Rot(Z=45) * main
        main = anchor(main, TOP)
        back_face = main.faces().filter_by(Axis.Y).sort_by(Axis.Y).first
        back_wedge = loft([back_face, Vertex(0, -self.length/2-self.depth)])
        front_face = main.faces().filter_by(Axis.Y).sort_by(Axis.Y).last
        front_wedge = loft([front_face, Vertex(0, self.length/2+self.depth)])
        main = main + [back_wedge, front_wedge]
        main = Rot(Y=180) * main
        return main
    def make_negative(self):
        if self.snap_tolerance == 0:
            return Rot(Y=180) * self.main_part
        main = offset(self.main_part, -self.snap_tolerance)
        main = anchor(main, BOT)
        main = Rot(Y=180) * main
        return main

cli = CommonPartCLI(BoardSnapClip)
make_default_model = cli.remake_with_args
if __name__ == "__main__":
    cli.main()
