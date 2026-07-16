"""Application composition for the Maya auto-limb builder."""

from .core import CoreMixin
from .rig import RigMixin
from .roll import RollMixin
from .stretch import StretchMixin
from .ui import UiMixin


class AutoLimbBuilder(UiMixin, StretchMixin, RollMixin, RigMixin, CoreMixin):
    def __init__(self):

        # MAIN VARIABLES
        self.main_layout = None

        self.type_menu = None

        self.solver_menu = None

        # CUSTOM VARIABLES
        self.custom_root_field = None
        self.custom_start_menu = None
        self.custom_end_menu = None
        self.custom_ik_check = None
        self.custom_fk_check = None
        self.custom_stretch_check = None
        self.custom_roll_check = None
        self.custom_solver_menu = None
        self.custom_stretch_mode_menu = None
        self.custom_stretch_ctrl_field = None
        self.custom_stretch_ctrl = None
        self.custom_stretch_start_field = None
        self.custom_stretch_end_field = None
        self.custom_stretch_start_joint = None
        self.custom_stretch_end_joint = None

        self.custom_roll_mode_menu = None
        self.custom_roll_start_field = None
        self.custom_roll_end_field = None
        self.custom_roll_start_joint = None
        self.custom_roll_end_joint = None

        self.custom_primary_axis_menu = None
        self.custom_secondary_axis_menu = None
        self.custom_secondary_world_menu = None

        # Store real joint names here.
        # UI menus only display short names.
        self.custom_root_joint = None
        self.custom_chain = []


# Backward-compatible name used by the original script.
VincentLimbBuilder = AutoLimbBuilder
