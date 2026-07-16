"""Maya auto-limb builder module."""

import maya.cmds as cmds


class RigMixin(object):
    def build_fk(self, source_chain):
        fk_chain = self.duplicate_limb_chain(
            source_chain,
            "_FK"
        )

        cmds.group(
            fk_chain[0],
            name=self.short_name(fk_chain[0]) + "_grp"
        )

        print("Created FK chain:", fk_chain)
        return fk_chain

    def build_ik(self, source_chain, solver):
        ik_chain = self.duplicate_limb_chain(
            source_chain,
            "_IK"
        )

        grp = cmds.group(
            ik_chain[0],
            name=self.short_name(ik_chain[0]) + "_grp"
        )

        if len(ik_chain) >= 3:
            end = ik_chain[2]
        else:
            end = ik_chain[-1]

        ikh = cmds.ikHandle(
            name=self.short_name(ik_chain[0]) + "_ikh",
            startJoint=ik_chain[0],
            endEffector=end,
            solver=solver
        )[0]

        cmds.parent(ikh, grp)

        print("Created IK chain:", ik_chain)
        print("Created IK handle:", ikh)
        return ik_chain, ikh

    def build_custom_fk(self, chain, primary_axis):
        """
        Build a custom FK joint chain and create FK controls automatically.
        """
        fk_chain = self.duplicate_custom_range(
            chain,
            "_FK"
        )

        if not fk_chain:
            cmds.warning("Failed to create Custom FK chain.")
            return None

        fk_joint_group = cmds.group(
            fk_chain[0],
            name=self.short_name(fk_chain[0]) + "_grp"
        )

        fk_ctrls, fk_ctrl_root = self.create_fk_controls(
            fk_chain,
            primary_axis
        )

        print("Created Custom FK chain:", fk_chain)
        print("Created Custom FK controls:", fk_ctrls)

        return {
            "chain": fk_chain,
            "joint_group": fk_joint_group,
            "controls": fk_ctrls,
            "control_root": fk_ctrl_root
        }

    def build_custom_ik(self, chain, solver):
        """
        Build a custom IK joint chain and IK handle.
        """
        ik_chain = self.duplicate_custom_range(
            chain,
            "_IK"
        )

        if not ik_chain:
            cmds.warning("Failed to create Custom IK chain.")
            return None, None

        ik_joint_group = cmds.group(
            ik_chain[0],
            name=self.short_name(ik_chain[0]) + "_grp"
        )

        ikh = cmds.ikHandle(
            name=self.short_name(ik_chain[0]) + "_ikh",
            startJoint=ik_chain[0],
            endEffector=ik_chain[-1],
            solver=solver
        )[0]

        cmds.parent(
            ikh,
            ik_joint_group
        )

        print("Created Custom IK chain:", ik_chain)
        print("Created Custom IK handle:", ikh)

        return ik_chain, ikh

    def get_custom_selected_chain(self):
        """
        Read the Start and End menus and return the selected joint range.
        """
        if not self.custom_chain:
            cmds.warning(
                "Please load a root joint chain first."
            )
            return []

        start_index = cmds.optionMenu(
            self.custom_start_menu,
            query=True,
            select=True
        ) - 1

        end_index = cmds.optionMenu(
            self.custom_end_menu,
            query=True,
            select=True
        ) - 1

        if start_index < 0 or end_index < 0:
            cmds.warning(
                "Please choose Start and End joints."
            )
            return []

        if start_index >= end_index:
            cmds.warning(
                "Start Joint must be above End Joint."
            )
            return []

        return self.custom_chain[
            start_index:end_index + 1
        ]

    def get_custom_build_options(self):
        """
        Read Custom IK/FK settings from the UI.
        """
        add_ik = cmds.checkBox(
            self.custom_ik_check,
            query=True,
            value=True
        )

        add_fk = cmds.checkBox(
            self.custom_fk_check,
            query=True,
            value=True
        )

        solver = cmds.optionMenu(
            self.custom_solver_menu,
            query=True,
            value=True
        )

        primary_axis = cmds.optionMenu(
            self.custom_primary_axis_menu,
            query=True,
            value=True
        )

        secondary_axis = cmds.optionMenu(
            self.custom_secondary_axis_menu,
            query=True,
            value=True
        )

        return {
            "add_ik": add_ik,
            "add_fk": add_fk,
            "solver": solver,
            "primary_axis": primary_axis,
            "secondary_axis": secondary_axis
        }

    def build_custom_ik_system(self, chain, solver):
        """
        Build the custom IK chain, IK handle and IK control.
        """
        ik_chain, ik_handle = self.build_custom_ik(
            chain,
            solver
        )

        if not ik_chain or not ik_handle:
            return None

        control_result = self.create_custom_ik_control(
            ik_chain,
            ik_handle
        )

        return {
            "chain": ik_chain,
            "handle": ik_handle,
            "control_result": control_result
        }

    def build_custom_fk_system(self, chain, primary_axis):
        """
        Build the custom FK chain and its controls.
        """
        return self.build_custom_fk(
            chain,
            primary_axis
        )

    def build_parentCons_IKFK(
        self,
        bind_chain,
        ik_chain=None,
        fk_chain=None
    ):
        constraints = []

        for i, bind_jnt in enumerate(bind_chain):
            targets = []

            if ik_chain:
                targets.append(ik_chain[i])

            if fk_chain:
                targets.append(fk_chain[i])

            if not targets:
                continue

            constraint = cmds.parentConstraint(
                *(targets + [bind_jnt]),
                maintainOffset=True
            )[0]

            constraints.append(constraint)

            print(
                "Created Parent Constraint:",
                targets,
                "->",
                bind_jnt,
                constraint
            )

        return constraints

    def connect_ikfk_switch(
        self,
        switch_ctrl,
        constraints,
        ik_chain,
        fk_chain,
        fk_text=None,
        ik_text=None
    ):
        reverse_node = cmds.createNode(
            "reverse",
            name=switch_ctrl + "_reverse"
        )

        cmds.connectAttr(
            switch_ctrl + ".ikFk",
            reverse_node + ".inputX",
            force=True
        )


        for i, constraint in enumerate(constraints):
            aliases = cmds.parentConstraint(
                constraint,
                query=True,
                weightAliasList=True
            ) or []

            targets = cmds.parentConstraint(
                constraint,
                query=True,
                targetList=True
            ) or []

            print("Constraint:", constraint)
            print("Targets:", targets)
            print("Aliases:", aliases)


            for target, alias in zip(targets, aliases):
                target_short = self.short_name(target)

                if target_short == self.short_name(ik_chain[i]):
                    cmds.connectAttr(
                        switch_ctrl + ".ikFk",
                        constraint + "." + alias,
                        force=True
                    )

                elif target_short == self.short_name(fk_chain[i]):
                    cmds.connectAttr(
                        reverse_node + ".outputX",
                        constraint + "." + alias,
                        force=True
                    )

        if ik_text:
            cmds.connectAttr(
                switch_ctrl + ".ikFk",
                ik_text + ".visibility",
                force=True
            )

        if fk_text:
            cmds.connectAttr(
                reverse_node + ".outputX",
                fk_text + ".visibility",
                force=True
            )

        print("Connected IK/FK switch:", switch_ctrl)
        return reverse_node

    def create_square_ctrl(self, name, size=2.0):
        points = [
            (-size, 0, -size),
            ( size, 0, -size),
            ( size, 0,  size),
            (-size, 0,  size),
            (-size, 0, -size)
        ]

        return cmds.curve(
            name=name,
            degree=1,
            point=points
        )

    def create_triangle_ctrl(self, name, size=1.5):
        points = [
            (0, size, 0),
            (-size, -size, 0),
            (size, -size, 0),
            (0, size, 0)
        ]

        return cmds.curve(
            name=name,
            degree=1,
            point=points
        )

    def create_fk_controls(self, fk_chain, primary_axis):
        fk_ctrls = []
        fk_offsets = []
        previous_ctrl = None

        normal_map = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1)
        }

        normal = normal_map.get(primary_axis, (1, 0, 0))

        for fk_joint in fk_chain:
            ctrl = cmds.circle(
                name=self.short_name(fk_joint) + "_ctrl",
                normal=normal,
                radius=1.5
            )[0]

            offset = cmds.group(
                ctrl,
                name=ctrl + "_offset"
            )

            self.match_group_to_object(
                offset,
                fk_joint
            )

            cmds.parentConstraint(
                ctrl,
                fk_joint,
                maintainOffset=False
            )

            # Put every next FK offset inside the previous FK control.
            if previous_ctrl:
                cmds.parent(
                    offset,
                    previous_ctrl
                )

            fk_ctrls.append(ctrl)
            fk_offsets.append(offset)
            previous_ctrl = ctrl

        print("Created FK controls:", fk_ctrls)

        return fk_ctrls, fk_offsets[0]

    def create_ik_controls(self, ik_chain, ik_handle):
        end_joint = ik_chain[2]

        wrist_ctrl = self.create_square_ctrl(
            self.short_name(end_joint) + "_ctrl",
            size=1.8
        )

        wrist_offset = cmds.group(
            wrist_ctrl,
            name=wrist_ctrl + "_offset"
        )

        self.match_group_to_object(
            wrist_offset,
            end_joint
        )

        # Square control moves the IK handle.
        cmds.parentConstraint(
            wrist_ctrl,
            ik_handle,
            maintainOffset=True
        )

        # Square control also controls the wrist orientation.
        cmds.orientConstraint(
            wrist_ctrl,
            end_joint,
            maintainOffset=True
        )

        ik_ctrl_grp = cmds.group(
            wrist_offset,
            name=self.short_name(ik_chain[0]) + "_IK_controls_grp"
        )

        print("Created IK wrist control:", wrist_ctrl)

        return wrist_ctrl, ik_ctrl_grp

    def connect_control_visibility(
        self,
        switch_ctrl,
        reverse_node,
        ik_ctrl_group,
        fk_ctrl_root,
        ik_joint_group=None,
        fk_joint_group=None
    ):
        # ikFk = 1: show IK controls.
        cmds.connectAttr(
            switch_ctrl + ".ikFk",
            ik_ctrl_group + ".visibility",
            force=True
        )

        # ikFk = 0: show FK controls.
        cmds.connectAttr(
            reverse_node + ".outputX",
            fk_ctrl_root + ".visibility",
            force=True
        )

        # ikFk = 1: show IK joint chain.
        if ik_joint_group:
            cmds.connectAttr(
                switch_ctrl + ".ikFk",
                ik_joint_group + ".visibility",
                force=True
            )

        # ikFk = 0: show FK joint chain.
        if fk_joint_group:
            cmds.connectAttr(
                reverse_node + ".outputX",
                fk_joint_group + ".visibility",
                force=True
            )

    def build_ikfk_system(
        self,
        bind_chain,
        solver,
        primary_axis,
        secondary_axis,
        rig_type
    ):
        fk_chain = self.build_fk(bind_chain)

        ik_chain, ik_handle = self.build_ik(
            bind_chain,
            solver
        )

        constraints = self.build_parentCons_IKFK(
            bind_chain,
            ik_chain,
            fk_chain
        )

        switch_ctrl, fk_text, ik_text = self.create_ikfk_switch_ctrl(
            bind_chain[-1]
        )

        reverse_node = self.connect_ikfk_switch(
            switch_ctrl,
            constraints,
            ik_chain,
            fk_chain,
            fk_text,
            ik_text
        )

        fk_ctrls, fk_ctrl_root = self.create_fk_controls(
            fk_chain,
            primary_axis
        )

        wrist_ctrl, ik_ctrl_group = self.create_ik_controls(
            ik_chain,
            ik_handle
        )

        self.build_ik_stretch(
            ik_chain,
            wrist_ctrl,
            switch_ctrl,
            primary_axis
        )

        ik_joint_group = (
            cmds.listRelatives(
                ik_chain[0],
                parent=True,
                fullPath=True
            ) or [None]
        )[0]

        fk_joint_group = (
            cmds.listRelatives(
                fk_chain[0],
                parent=True,
                fullPath=True
            ) or [None]
        )[0]

        self.connect_control_visibility(
            switch_ctrl,
            reverse_node,
            ik_ctrl_group,
            fk_ctrl_root,
            ik_joint_group,
            fk_joint_group
        )

        roll_segments = self.build_simple_roll_joints(
            bind_chain
        )

        self.set_roll_joint_rotate_orders(
            roll_segments,
            primary_axis
        )

        self.setup_roll_midpoint_positions(
            bind_chain,
            ik_chain,
            roll_segments,
            primary_axis
        )

        aim_locators = self.create_roll_aim_locators(
            bind_chain,
            roll_segments,
            secondary_axis,
            rig_type
        )

        self.aim_simple_roll_segments(
            bind_chain,
            roll_segments,
            aim_locators,
            primary_axis,
            secondary_axis,
            rig_type
        )

        # Build only the upper-arm / upper-leg follow chain for now.
        self.create_upper_roll_follow_chain(
            roll_segments[0],
            aim_locators[0],
            bind_chain[1],
            secondary_axis,
            distance=2.0
        )

        self.setup_bicep_roll(
            bind_chain,
            roll_segments[0],
            switch_ctrl,
            primary_axis
        )

        self.setup_radius_roll(
            roll_segments[1],
            switch_ctrl,
            primary_axis
        )

        cmds.confirmDialog(
            title="Done",
            message="IK/FK system created.",
            button=["OK"]
        )

    def create_ikfk_switch_ctrl(self, end_joint):
        points = [
            (-2.0,  0.5, 0.0),
            ( 1.0,  0.5, 0.0),

            ( 1.0,  1.2, 0.0),
            ( 2.5,  0.0, 0.0),
            ( 1.0, -1.2, 0.0),
            ( 1.0, -0.5, 0.0),

            (-2.0, -0.5, 0.0),

            (-2.0, -1.2, 0.0),
            (-3.5,  0.0, 0.0),
            (-2.0,  1.2, 0.0),
            (-2.0,  0.5, 0.0),

            (-2.0,  0.5, 0.0)
        ]

        ctrl = cmds.curve(
            name=self.short_name(end_joint) + "_IKFK_switch_ctrl",
            degree=1,
            point=points
        )

        offset = cmds.group(
            ctrl,
            name=ctrl + "_offset"
        )

        temp_constraint = cmds.parentConstraint(
            end_joint,
            offset,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        if not cmds.attributeQuery(
            "ikFk",
            node=ctrl,
            exists=True
        ):
            cmds.addAttr(
                ctrl,
                longName="ikFk",
                niceName="IK / FK",
                attributeType="double",
                minValue=0,
                maxValue=1,
                defaultValue=0,
                keyable=True
            )

        # Create text labels beside the switch.
        fk_text = cmds.textCurves(
            font="Arial",
            text="FK",
            name=ctrl + "_FK_text"
        )[0]

        ik_text = cmds.textCurves(
            font="Arial",
            text="IK",
            name=ctrl + "_IK_text"
        )[0]

        # Make the labels smaller.
        cmds.scale(
            0.5, 0.5, 0.5,
            fk_text,
            relative=True
        )

        cmds.scale(
            0.5, 0.5, 0.5,
            ik_text,
            relative=True
        )

        # Parent labels under the switch first.
        cmds.parent(
            fk_text,
            ik_text,
            ctrl
        )

        # Keep both labels directly above the switch.
        cmds.setAttr(fk_text + ".translateX", -1.4)
        cmds.setAttr(fk_text + ".translateY", 1.6)
        cmds.setAttr(fk_text + ".translateZ", 0.0)

        cmds.setAttr(ik_text + ".translateX", 0.4)
        cmds.setAttr(ik_text + ".translateY", 1.6)
        cmds.setAttr(ik_text + ".translateZ", 0.0)

        print("Created IK/FK switch control:", ctrl)
        print("Added attribute:", ctrl + ".ikFk")

        return ctrl, fk_text, ik_text
