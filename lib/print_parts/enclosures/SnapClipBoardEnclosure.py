# Enclosure for a board, secured by snap clips
import cad_common
from build123d import *
from bd_common import *

from dataclasses import dataclass, make_dataclass, fields

from .SnapClipBoardStandoff import SnapClipBoardStandoff

@dataclass(kw_only=True)
class _UnAssembled(SnapClipBoardStandoff):
    top_clearance: float = 3
    top_inset_amount: float = 2
    lid_tolerance: float = 0
    def init_params(self):
        super().init_params()
        self.wall_h = self.board_thickness + max(self.top_clearance, 2*self.snap.width) + self.bot_clearance

    def make(self):
        super().make()
        # Unmangle
        last_components = getattr(self, f"_{self.__class__.__base__.__name__}__components")
        def make_next_step(left_attach_face, left_attach_plane,
                right_attach_face, right_attach_plane,
                main, main_w_snaps,
                base_sk, inner_base_sk,
            **kwargs):
            slot = self.snap.make_negative()
            left_slots = (
                left_attach_plane * Pos(Y=self.snap_distance/2) * slot +
                left_attach_plane * Pos(Y=-self.snap_distance/2) * slot
            )
            left_slots = connect_to(left_slots, left_attach_face, TOP+RIGHT, TOP)
            right_slots = (
                right_attach_plane * Pos(Y=self.snap_distance/2) * slot +
                right_attach_plane * Pos(Y=-self.snap_distance/2) * slot
            )
            right_slots = connect_to(right_slots, right_attach_face, TOP+LEFT, TOP)
            back_attach_face = main.faces().filter_by(Axis.Y).sort_by(Axis.Y)[-2]
            back_attach_plane = Plane(back_attach_face, x_dir=(0, 0, -1))
            back_slot = connect_to(back_attach_plane*slot, back_attach_face, TOP+FRONT, TOP)
            front_attach_face = main.faces().filter_by(Axis.Y).sort_by(Axis.Y)[1]
            front_attach_plane = Plane(front_attach_face, x_dir=(0, 0, -1))
            front_slot = connect_to(front_attach_plane*slot, front_attach_face, TOP+BACK, TOP)
            main_w_snaps -= [left_slots, right_slots, back_slot, front_slot]

            lid = extrude(base_sk, self.shell_thickness)
            lid_wedge_sk = (
                offset(inner_base_sk, -self.lid_tolerance) - 
                offset(inner_base_sk, -self.top_inset_amount)
                )
            lid_wedge = extrude(lid_wedge_sk, -self.snap.width)
            lid_left_attach_face = lid_wedge.faces().filter_by(Axis.X).sort_by(Axis.X)[0]
            lid_left_attach_plane = Plane(lid_left_attach_face, x_dir=(0, 0, -1))
            lid_left_snaps = (
                lid_left_attach_plane * Pos(Y=self.snap_distance/2) * self.snap + 
                lid_left_attach_plane * Pos(Y=-self.snap_distance/2) * self.snap
            )
            lid_right_attach_face = lid_wedge.faces().filter_by(Axis.X).sort_by(Axis.X)[-1]
            lid_right_attach_plane = Plane(lid_right_attach_face, x_dir=(0, 0, -1))
            lid_right_snaps = (
                lid_right_attach_plane * Pos(Y=self.snap_distance/2) * self.snap + 
                lid_right_attach_plane * Pos(Y=-self.snap_distance/2) * self.snap
            )
            lid_front_attach_face = lid_wedge.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0]
            lid_front_attach_plane = Plane(lid_front_attach_face, x_dir=(0, 0, -1))
            lid_front_snaps = (
                lid_front_attach_plane * self.snap
            )
            lid_back_attach_face = lid_wedge.faces().filter_by(Axis.Y).sort_by(Axis.Y)[-1]
            lid_back_attach_plane = Plane(lid_back_attach_face, x_dir=(0, 0, -1))
            lid_back_snaps = (
                lid_back_attach_plane * self.snap
            )
            lid += [lid_wedge, lid_left_snaps, lid_right_snaps, lid_front_snaps, lid_back_snaps]
            lid = Pos(Z=5)*connect_to(lid, main_w_snaps, BOT, TOP)
            self.base = main_w_snaps
            self.lid = lid
            return main_w_snaps
        return make_next_step(**last_components)

def _make(self):
    parts = init_dataclass_from(_UnAssembled, self)
    return [(parts.base, "base"), (parts.lid, "lid")]

SnapClipBoardEnclosure = make_dataclass(
    "SnapClipBoardEnclosure", [
        (f.name, f.type, f)
        for f in fields(_UnAssembled)],
    bases=(CommonAssembly,), namespace={
        "make": _make
    }
)
cli = CommonAssemblyCLI(SnapClipBoardEnclosure)
make_default_model = cli.remake_with_args
if __name__ == "__main__":
    cli.main()