"""Maya auto-limb builder module."""

import maya.cmds as cmds

from .config import WINDOW_NAME


class UiMixin(object):
    def clear_ui(self):
        children = cmds.columnLayout(
            self.main_layout,
            query=True,
            childArray=True
        ) or []

        for child in children:
            if cmds.control(child, exists=True) or cmds.layout(child, exists=True):
                cmds.deleteUI(child)

        cmds.setParent(self.main_layout)

    def rebuild_custom_joint_menus(self):
        """
        Rebuild Start / End optionMenus from loaded custom chain.
        UI displays short names, but build uses index to get real joint from self.custom_chain.
        """
        if not self.custom_start_menu or not self.custom_end_menu:
            return

        # Delete old menuItems
        for menu in [self.custom_start_menu, self.custom_end_menu]:
            items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
            for item in items:
                cmds.deleteUI(item)

        for jnt in self.custom_chain:
            cmds.menuItem(label=self.short_name(jnt), parent=self.custom_start_menu)

        for jnt in self.custom_chain:
            cmds.menuItem(label=self.short_name(jnt), parent=self.custom_end_menu)

        if len(self.custom_chain) >= 2:
            cmds.optionMenu(self.custom_start_menu, edit=True, select=1)
            cmds.optionMenu(self.custom_end_menu, edit=True, select=len(self.custom_chain))

    def show_main_page(self):
        self.clear_ui()

        cmds.text(label="Vincent Limb Builder", height=30, align="center")
        cmds.separator(height=8, style="in")

        cmds.frameLayout(
            label="Standard Limb",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

        self.type_menu = cmds.optionMenu(label="Type")
        cmds.menuItem(label="Arm")
        cmds.menuItem(label="Leg")

        self.solver_menu = cmds.optionMenu(label="IK Solver")
        cmds.menuItem(label="ikRPsolver")
        cmds.menuItem(label="ikSCsolver")

        self.primary_axis_menu = cmds.optionMenu(label="Primary Axis")
        cmds.menuItem(label="X")
        cmds.menuItem(label="Y")
        cmds.menuItem(label="Z")

        self.secondary_axis_menu = cmds.optionMenu(label="Secondary Axis")
        cmds.menuItem(label="X")
        cmds.menuItem(label="Y")
        cmds.menuItem(label="Z")
        cmds.optionMenu(
            self.secondary_axis_menu,
            edit=True,
            value="Y"
        )

        self.secondary_world_menu = cmds.optionMenu(
            label="Secondary Axis World Orientation"
        )
        cmds.menuItem(label="+X")
        cmds.menuItem(label="-X")
        cmds.menuItem(label="+Y")
        cmds.menuItem(label="-Y")
        cmds.menuItem(label="+Z")
        cmds.menuItem(label="-Z")
        cmds.optionMenu(
            self.secondary_world_menu,
            edit=True,
            value="+Y"
        )

        cmds.text(
            label="Select root joint, then build.\nStandard IK handle goes from joint 1 to joint 3.",
            align="left"
        )

        cmds.button(
            label="Build Standard Arm / Leg",
            height=45,
            command=self.build_standard
        )

        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(height=10, style="in")

        cmds.frameLayout(
            label="Custom",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(adjustableColumn=True, rowSpacing=8)

        cmds.text(
            label="Custom: select one root joint, load connected chain, then choose a joint segment.",
            align="left"
        )

        cmds.button(
            label="Go To Custom Page",
            height=45,
            command=lambda *args: self.show_custom_page()
        )

        cmds.setParent("..")
        cmds.setParent("..")

    def build_standard(self, *args):
        rig_type = cmds.optionMenu(
            self.type_menu,
            query=True,
            value=True
        )

        solver = cmds.optionMenu(
            self.solver_menu,
            query=True,
            value=True
        )

        primary_axis = cmds.optionMenu(
            self.primary_axis_menu,
            query=True,
            value=True
        )

        secondary_axis = cmds.optionMenu(
            self.secondary_axis_menu,
            query=True,
            value=True
        )

        secondary_world = cmds.optionMenu(
            self.secondary_world_menu,
            query=True,
            value=True
        )

        if primary_axis == secondary_axis:
            cmds.warning(
                "Primary Axis and Secondary Axis cannot be the same."
            )
            return

        root = self.selected_joint()
        if not root:
            return

        full_chain = self.get_first_child_chain(root)

        if rig_type == "Arm":
            if len(full_chain) < 3:
                cmds.warning("Arm needs at least 3 joints.")
                return

            bind_chain = full_chain[:3]

        elif rig_type == "Leg":
            if len(full_chain) < 4:
                cmds.warning("Leg needs at least 4 joints.")
                return

            bind_chain = full_chain[:4]

        print("Standard Type:", rig_type)
        print("Bind Chain:", bind_chain)
        print("Solver:", solver)
        print("Primary Axis:", primary_axis)
        print("Secondary Axis:", secondary_axis)
        print(
            "Secondary Axis World Orientation:",
            secondary_world
        )

        self.build_ikfk_system(
            bind_chain,
            solver,
            primary_axis,
            secondary_axis,
            rig_type
        )

    def show_custom_page(self):
        self.clear_ui()

        self.custom_root_joint = None
        self.custom_chain = []

        self.custom_stretch_ctrl = None
        self.custom_stretch_start_joint = None
        self.custom_stretch_end_joint = None

        self.custom_roll_start_joint = None
        self.custom_roll_end_joint = None

        cmds.text(
            label="Custom Limb Builder",
            height=30,
            align="center"
        )

        cmds.separator(
            height=8,
            style="in"
        )

        # =====================================================
        # Build Custom IK / FK
        # =====================================================
        cmds.frameLayout(
            label="Build Custom IK / FK",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=8
        )

        self.custom_root_field = cmds.textFieldButtonGrp(
            label="Root Joint",
            buttonLabel="Load Selected Root",
            text="",
            buttonCommand=self.load_custom_root_chain
        )

        self.custom_start_menu = cmds.optionMenu(
            label="Start Joint"
        )

        self.custom_end_menu = cmds.optionMenu(
            label="End Joint"
        )

        self.custom_ik_check = cmds.checkBox(
            label="Add IK",
            value=True,
            changeCommand=self.update_custom_solver_visibility
        )

        self.custom_fk_check = cmds.checkBox(
            label="Add FK",
            value=False
        )

        self.custom_solver_menu = cmds.optionMenu(
            label="IK Solver"
        )
        cmds.menuItem(label="ikRPsolver")
        cmds.menuItem(label="ikSCsolver")

        cmds.button(
            label="Build Custom Segment",
            height=42,
            command=self.build_custom
        )

        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(
            height=10,
            style="in"
        )

        # =====================================================
        # Shared Axis Settings
        # =====================================================
        cmds.frameLayout(
            label="Axis Settings",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=8
        )

        self.custom_primary_axis_menu = cmds.optionMenu(
            label="Primary Axis"
        )
        cmds.menuItem(label="X")
        cmds.menuItem(label="Y")
        cmds.menuItem(label="Z")

        self.custom_secondary_axis_menu = cmds.optionMenu(
            label="Secondary Axis"
        )
        cmds.menuItem(label="X")
        cmds.menuItem(label="Y")
        cmds.menuItem(label="Z")

        cmds.optionMenu(
            self.custom_secondary_axis_menu,
            edit=True,
            value="Y"
        )

        self.custom_secondary_world_menu = cmds.optionMenu(
            label="Secondary World Orientation"
        )

        for label in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
            cmds.menuItem(label=label)

        cmds.optionMenu(
            self.custom_secondary_world_menu,
            edit=True,
            value="+Y"
        )

        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(
            height=10,
            style="in"
        )

        # =====================================================
        # Independent Custom Stretch
        # =====================================================
        cmds.frameLayout(
            label="Custom Stretch Tool",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=8
        )

        self.custom_stretch_start_field = cmds.textFieldButtonGrp(
            label="Stretch Start Joint",
            buttonLabel="Load Selected",
            text="",
            buttonCommand=self.load_custom_stretch_start_joint
        )

        self.custom_stretch_end_field = cmds.textFieldButtonGrp(
            label="Stretch End Joint",
            buttonLabel="Load Selected",
            text="",
            buttonCommand=self.load_custom_stretch_end_joint
        )

        self.custom_stretch_ctrl_field = cmds.textFieldButtonGrp(
            label="IK Control",
            buttonLabel="Load Selected",
            text="",
            buttonCommand=self.load_custom_stretch_control
        )

        cmds.button(
            label="Add Stretch",
            height=42,
            command=self.add_custom_stretch
        )

        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(
            height=10,
            style="in"
        )

        # =====================================================
        # Independent Custom Roll
        # =====================================================
        cmds.frameLayout(
            label="Custom Roll Joint Tool",
            collapsable=False,
            marginWidth=10,
            marginHeight=10
        )

        cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=8
        )

        self.custom_roll_start_field = cmds.textFieldButtonGrp(
            label="Roll Start Joint",
            buttonLabel="Load Selected",
            text="",
            buttonCommand=self.load_custom_roll_start_joint
        )

        self.custom_roll_end_field = cmds.textFieldButtonGrp(
            label="Roll End Joint",
            buttonLabel="Load Selected",
            text="",
            buttonCommand=self.load_custom_roll_end_joint
        )

        self.custom_roll_mode_menu = cmds.optionMenu(
            label="Roll Type"
        )

        cmds.menuItem(label="Upper Segment Roll")
        cmds.menuItem(label="Lower Segment Roll")

        cmds.button(
            label="Add Roll Joint",
            height=42,
            command=self.add_custom_roll_joint
        )

        cmds.setParent("..")
        cmds.setParent("..")

        cmds.separator(
            height=10,
            style="in"
        )

        cmds.button(
            label="Back",
            height=35,
            command=lambda *args: self.show_main_page()
        )

        self.update_custom_solver_visibility()

    def update_custom_solver_visibility(self, *args):
        if not self.custom_ik_check or not self.custom_solver_menu:
            return

        if not cmds.checkBox(self.custom_ik_check, exists=True):
            return

        add_ik = cmds.checkBox(self.custom_ik_check, query=True, value=True)
        cmds.optionMenu(self.custom_solver_menu, edit=True, visible=add_ik)

    def load_custom_root_chain(self, *args):
        root = self.selected_joint()
        if not root:
            return

        self.custom_root_joint = root
        self.custom_chain = self.get_first_child_chain(root)

        if len(self.custom_chain) < 2:
            cmds.warning("Loaded chain needs at least 2 joints.")
            return

        cmds.textFieldButtonGrp(
            self.custom_root_field,
            edit=True,
            text=self.short_name(root)
        )

        self.rebuild_custom_joint_menus()

        print("Loaded Custom Chain:")
        for i, jnt in enumerate(self.custom_chain):
            print("%s: %s" % (i, jnt))

    def build_custom(self, *args):
        """
        Main Custom build entry.

        This method coordinates the build while smaller methods handle
        chain selection, UI options, IK creation and FK creation.
        """
        chain = self.get_custom_selected_chain()

        if not chain:
            return None

        options = self.get_custom_build_options()

        if not options["add_ik"] and not options["add_fk"]:
            cmds.warning(
                "Choose Add IK, Add FK, or both."
            )
            return None

        build_result = {
            "bind_chain": chain,
            "ik": None,
            "fk": None
        }

        if options["add_ik"]:
            build_result["ik"] = self.build_custom_ik_system(
                chain,
                options["solver"]
            )

        if options["add_fk"]:
            build_result["fk"] = self.build_custom_fk_system(
                chain,
                options["primary_axis"]
            )

        print("Custom Build Result:")
        print(build_result)

        cmds.confirmDialog(
            title="Done",
            message="Custom IK / FK build finished.",
            button=["OK"]
        )

        return build_result

    def show(self):
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)

        cmds.window(
            WINDOW_NAME,
            title="Vincent Limb Builder",
            widthHeight=(430, 500)
        )

        self.main_layout = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=10
        )

        self.show_main_page()

        cmds.showWindow(WINDOW_NAME)
