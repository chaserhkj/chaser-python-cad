import cad_common
from build123d import *
from bd_common import *

from dataclasses import dataclass
from ..BoardSnapClip import BoardSnapClip
from types import SimpleNamespace

# Snap-Clip secured Standoff for bottom clearance of boards
@dataclass(kw_only=True)
class SnapClipBoardStandoff(CommonPart):
    shell_thickness: float = 2
    inner_w: float = 50
    inner_l: float = 50
    board_tolerance: float = 0.2
    board_thickness: float = 1.6
    bot_clearance: float = 3
    # Bottom standoff pattern, sketch or float number as inset amount
    bot_standoff_pattern: Union[float, Sketch] = 2.0
    snap_length: float = 10
    snap_depth: float = 1
    snap_tolerance: float = 0
    def init_params(self):
        self.adjusted_inner_w = self.inner_w + 2*self.board_tolerance
        self.adjusted_inner_l = self.inner_l + 2*self.board_tolerance
        self.outer_w = self.adjusted_inner_w + 2*self.shell_thickness
        self.outer_l = self.adjusted_inner_l + 2*self.shell_thickness
        self.snap = BoardSnapClip(length=self.snap_length,
                            depth=self.snap_depth,
                            snap_tolerance=self.snap_tolerance)
        self.wall_h = self.board_thickness + self.snap.width + self.bot_clearance
        self.snap_distance = self.snap.full_length*3
        assert self.adjusted_inner_l > self.snap.full_length * 4, "snap_length is too big!"

    def make(self):
        inner_base_sk = Rectangle(self.adjusted_inner_w, self.adjusted_inner_l)
        base_sk = offset(inner_base_sk, self.shell_thickness)
        walls_sk = base_sk - inner_base_sk
        base = extrude(base_sk, self.shell_thickness)
        base = anchor(base, TOP)
        walls = extrude(walls_sk, self.wall_h)
        if isinstance(self.bot_standoff_pattern, float):
            bot_standoff_sk = inner_base_sk - offset(inner_base_sk, -self.bot_standoff_pattern)
        else:
            bot_standoff_sk = self.bot_standoff_pattern
        bot_standoff = extrude(bot_standoff_sk, self.bot_clearance)
        main = base + [walls, bot_standoff]
        left_attach_face = main.faces().filter_by(Axis.X).sort_by(Axis.X)[1]
        left_attach_plane = Plane(left_attach_face, x_dir=(0, 0, -1))
        left_snap = left_attach_plane * self.snap
        left_snap = connect_to(left_snap, left_attach_face, LEFT+BOT, BOT)
        left_snap = Pos(Z=self.board_thickness)*left_snap
        right_attach_face = main.faces().filter_by(Axis.X).sort_by(Axis.X)[-2]
        right_attach_plane = Plane(right_attach_face, x_dir=(0, 0, -1))
        right_snap = right_attach_plane * self.snap
        right_snap = connect_to(right_snap, right_attach_face, RIGHT+BOT, BOT)
        right_snap = Pos(Z=self.board_thickness)*right_snap
        main_w_snaps = main + [left_snap, right_snap]

        self.__components = locals()

        return main_w_snaps

cli = CommonPartCLI(SnapClipBoardStandoff)
make_default_model = cli.remake_with_args
if __name__ == "__main__":
    cli.main()