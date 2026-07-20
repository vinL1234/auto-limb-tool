"""Maya auto-limb builder module."""

import maya.cmds as cmds


# Builds upper-arm and forearm roll joints with aim and follow behavior.
class RollMixin(object):
    def create_secondary_locator(
        self,
        joint,
        secondary_axis,
        name,
        distance=4.0
    ):
        locator = cmds.spaceLocator(
            name=name
        )[0]

        # Temporarily align position and orientation to the joint.
        temp_constraint = cmds.parentConstraint(
            joint,
            locator,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Move in the opposite direction of the selected secondary axis.
        cmds.move(
            -secondary_vector[0] * distance,
            -secondary_vector[1] * distance,
            -secondary_vector[2] * distance,
            locator,
            relative=True,
            objectSpace=True
        )

        return locator

    def create_roll_aim_locators(
        self,
        bind_chain,
        roll_segments,
        secondary_axis,
        rig_type
    ):
        if len(bind_chain) < 3 or len(roll_segments) < 2:
            cmds.warning(
                "Roll aim locators need three main joints and two roll segments."
            )
            return []

        if rig_type == "Arm":
            first_locator_name = "humerus_roll_aim_loc"
            second_locator_name = "elbow_roll_aim_loc"

        else:
            first_locator_name = "femur_roll_aim_loc"
            second_locator_name = "knee_roll_aim_loc"

        # First locator starts from the main root joint.
        first_locator = self.create_secondary_locator(
            bind_chain[0],
            secondary_axis,
            first_locator_name
        )

        # The lower segment has no roll root.
        # Use the wrist/end roll joint as the second locator source.
        wrist_roll_joint = roll_segments[1][1]

        second_locator = self.create_secondary_locator(
            wrist_roll_joint,
            secondary_axis,
            second_locator_name
        )

        # Parent the wrist aim locator under the last main joint (wrist/ankle).
        cmds.parent(
            second_locator,
            bind_chain[2]
        )

        print(
            "Created Roll Aim Locators:",
            first_locator,
            second_locator
        )

        return [
            first_locator,
            second_locator
        ]

    def duplicate_joint_only(self, source_joint, new_name):
        new_joint = cmds.duplicate(
            source_joint,
            parentOnly=True,
            name=new_name
        )[0]

        parent = cmds.listRelatives(
            new_joint,
            parent=True,
            fullPath=True
        ) or []

        if parent:
            new_joint = cmds.parent(
                new_joint,
                world=True
            )[0]

        return new_joint

    def create_simple_roll_segment(
        self,
        start_joint,
        end_joint,
        segment_name
    ):
        # Create a two-joint segment used to distribute limb twist.
        roll_root = self.duplicate_joint_only(
            start_joint,
            segment_name + "_roll_root_jnt"
        )

        temp_constraint = cmds.parentConstraint(
            start_joint,
            roll_root,
            maintainOffset=False
        )[0]
        cmds.delete(temp_constraint)

        roll_root = cmds.parent(
            roll_root,
            start_joint
        )[0]

        roll_mid = self.duplicate_joint_only(
            start_joint,
            segment_name + "_roll_mid_jnt"
        )

        start_position = cmds.xform(
            start_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        end_position = cmds.xform(
            end_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        midpoint = [
            (start_position[0] + end_position[0]) * 0.5,
            (start_position[1] + end_position[1]) * 0.5,
            (start_position[2] + end_position[2]) * 0.5
        ]

        cmds.xform(
            roll_mid,
            worldSpace=True,
            translation=midpoint
        )

        roll_mid = cmds.parent(
            roll_mid,
            roll_root
        )[0]

        print(
            "Created Roll Segment:",
            roll_root,
            roll_mid
        )

        return roll_root, roll_mid

    def create_forearm_roll_joints(
        self,
        elbow_joint,
        wrist_joint
    ):
        elbow_name = self.short_name(elbow_joint)
        wrist_name = self.short_name(wrist_joint)

        elbow_position = cmds.xform(
            elbow_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        wrist_position = cmds.xform(
            wrist_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        midpoint = [
            (elbow_position[0] + wrist_position[0]) * 0.5,
            (elbow_position[1] + wrist_position[1]) * 0.5,
            (elbow_position[2] + wrist_position[2]) * 0.5
        ]

        # Joint in the middle of the forearm.
        forearm_mid_roll = self.duplicate_joint_only(
            elbow_joint,
            elbow_name + "_forearm_mid_roll_jnt"
        )

        cmds.xform(
            forearm_mid_roll,
            worldSpace=True,
            translation=midpoint
        )

        forearm_mid_roll = cmds.parent(
            forearm_mid_roll,
            elbow_joint
        )[0]

        # Joint at the wrist position.
        wrist_roll = self.duplicate_joint_only(
            wrist_joint,
            wrist_name + "_roll_jnt"
        )

        temp_constraint = cmds.parentConstraint(
            wrist_joint,
            wrist_roll,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        wrist_roll = cmds.parent(
            wrist_roll,
            elbow_joint
        )[0]

        # These two roll joints are siblings.
        # Both are children of the main elbow joint.
        print(
            "Created Forearm Roll Joints:",
            forearm_mid_roll,
            wrist_roll,
            "Parent:",
            elbow_joint
        )

        return forearm_mid_roll, wrist_roll

    def rotate_order_primary_last(self, primary_axis):
        rotate_order_map = {
            "X": 1,  # YZX: X is last
            "Y": 3,  # XZY: Y is last
            "Z": 0   # XYZ: Z is last
        }

        return rotate_order_map.get(
            primary_axis,
            1
        )

    def set_roll_joint_rotate_orders(
        self,
        roll_segments,
        primary_axis
    ):
        rotate_order = self.rotate_order_primary_last(
            primary_axis
        )

        for segment in roll_segments:
            for roll_joint in segment:
                if cmds.objExists(roll_joint):
                    cmds.setAttr(
                        roll_joint + ".rotateOrder",
                        rotate_order
                    )

        print(
            "Set Roll Joint Rotate Order:",
            primary_axis,
            "last"
        )

    def build_simple_roll_joints(self, bind_chain):
        if len(bind_chain) < 3:
            cmds.warning(
                "Simple roll setup needs at least 3 joints."
            )
            return []

        first_name = self.short_name(bind_chain[0])

        # Upper segment remains a root + midpoint chain.
        first_segment = self.create_simple_roll_segment(
            bind_chain[0],
            bind_chain[1],
            first_name
        )

        # Lower segment has two sibling roll joints:
        # one at the midpoint and one at the wrist/end joint.
        second_segment = self.create_forearm_roll_joints(
            bind_chain[1],
            bind_chain[2]
        )

        print(
            "Created Roll Joints:",
            first_segment,
            second_segment
        )

        return [
            first_segment,
            second_segment
        ]

    def aim_simple_roll_segments(
        self,
        bind_chain,
        roll_segments,
        aim_locators,
        primary_axis,
        secondary_axis,
        rig_type
    ):
        if len(bind_chain) < 3:
            return

        if len(roll_segments) < 2 or len(aim_locators) < 2:
            return

        aim_vector = self.primary_axis_vector(
            primary_axis
        )

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Aim Constraint uses the opposite direction of Secondary Axis.
        up_vector = (
            -secondary_vector[0],
            -secondary_vector[1],
            -secondary_vector[2]
        )

        first_roll_root = roll_segments[0][0]

        # Lower segment:
        # [0] = forearm midpoint roll
        # [1] = wrist roll
        wrist_roll_joint = roll_segments[1][1]

        # Upper roll root aims toward elbow/knee.
        cmds.aimConstraint(
            bind_chain[1],
            first_roll_root,
            maintainOffset=False,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=aim_locators[0]
        )

        # Wrist roll aims backward toward elbow/knee.
        reverse_aim_vector = (
            -aim_vector[0],
            -aim_vector[1],
            -aim_vector[2]
        )

        # Arm wrist roll: maintainOffset=False
        # Leg ankle roll: maintainOffset=True
        keep_end_offset = rig_type == "Leg"

        cmds.aimConstraint(
            bind_chain[1],
            wrist_roll_joint,
            maintainOffset=keep_end_offset,
            aimVector=reverse_aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=aim_locators[1]
        )

        print(
            "Created Roll Aim Constraints:",
            first_roll_root,
            "->",
            bind_chain[1],
            wrist_roll_joint,
            "->",
            bind_chain[1]
        )

    def create_upper_roll_follow_chain(
        self,
        first_roll_segment,
        upper_aim_locator,
        target_joint,
        secondary_axis,
        distance=2.0
    ):
        roll_root = first_roll_segment[0]
        roll_mid = first_roll_segment[1]

        root_name = self.short_name(roll_root)
        mid_name = self.short_name(roll_mid)

        follow_root = self.duplicate_joint_only(
            roll_root,
            root_name.replace("_jnt", "") + "_follow_jnt"
        )

        follow_mid = self.duplicate_joint_only(
            roll_mid,
            mid_name.replace("_jnt", "") + "_follow_jnt"
        )

        # Make a clean follow hierarchy.
        follow_mid = cmds.parent(
            follow_mid,
            follow_root
        )[0]

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Move the follow chain in the same opposite-secondary direction
        # as the locator, but only halfway, so it sits between the
        # original roll joints and the locator.
        cmds.move(
            -secondary_vector[0] * distance,
            -secondary_vector[1] * distance,
            -secondary_vector[2] * distance,
            follow_root,
            relative=True,
            objectSpace=True
        )

        # Parent the upper-arm aim locator under the follow root.
        # Maya keeps its world position by default.
        cmds.parent(
            upper_aim_locator,
            follow_root
        )

        follow_ikh = cmds.ikHandle(
            name=root_name.replace("_jnt", "") + "_follow_ikh",
            startJoint=follow_root,
            endEffector=follow_mid,
            solver="ikRPsolver"
        )[0]

        # Zero the IK Handle pole vector values.
        for axis in "XYZ":
            pole_attr = follow_ikh + ".poleVector" + axis

            if cmds.objExists(pole_attr):
                cmds.setAttr(
                    pole_attr,
                    0
                )

        # Snap the IK Handle to the second main joint.
        temp_constraint = cmds.pointConstraint(
            target_joint,
            follow_ikh,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        # Parent the IK Handle under the second main joint.
        follow_ikh = cmds.parent(
            follow_ikh,
            target_joint
        )[0]

        print(
            "Created Upper Roll Follow Chain:",
            follow_root,
            follow_mid,
            follow_ikh
        )

        return follow_root, follow_mid, follow_ikh

    def setup_bicep_roll(
        self,
        bind_chain,
        first_roll_segment,
        switch_ctrl,
        primary_axis
    ):
        # Transfer part of the upper-arm rotation to the bicep roll joint.
        if len(bind_chain) < 2:
            cmds.warning(
                "Bicep roll needs at least two main joints."
            )
            return None

        if not first_roll_segment:
            cmds.warning(
                "Upper roll segment was not created."
            )
            return None

        humerus_joint = bind_chain[0]

        # first_roll_segment:
        # [0] = humerus roll root
        # [1] = bicep roll midpoint joint
        bicep_roll_joint = first_roll_segment[1]

        rotate_attr = self.primary_rotate_attribute(
            primary_axis
        )

        if not cmds.attributeQuery(
            "bicepRoll",
            node=switch_ctrl,
            exists=True
        ):
            cmds.addAttr(
                switch_ctrl,
                longName="bicepRoll",
                niceName="Bicep Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(humerus_joint) + "_bicep_roll_md"
        )

        # Humerus primary-axis rotation drives input1X.
        cmds.connectAttr(
            humerus_joint + "." + rotate_attr,
            multiply_node + ".input1X",
            force=True
        )

        # Animator multiplier drives input2X.
        cmds.connectAttr(
            switch_ctrl + ".bicepRoll",
            multiply_node + ".input2X",
            force=True
        )

        # Result drives bicep roll primary-axis rotation.
        cmds.connectAttr(
            multiply_node + ".outputX",
            bicep_roll_joint + "." + rotate_attr,
            force=True
        )

        print(
            "Created Bicep Roll Setup:",
            humerus_joint + "." + rotate_attr,
            "->",
            multiply_node,
            "->",
            bicep_roll_joint + "." + rotate_attr
        )

        return multiply_node

    def setup_radius_roll(
        self,
        second_roll_segment,
        switch_ctrl,
        primary_axis
    ):
        # Transfer wrist rotation through the forearm roll setup.
        if not second_roll_segment:
            cmds.warning(
                "Forearm roll joints were not created."
            )
            return None

        # second_roll_segment:
        # [0] = midpoint forearm/radius roll
        # [1] = wrist roll
        radius_roll_joint = second_roll_segment[0]
        wrist_roll_joint = second_roll_segment[1]

        rotate_attr = self.primary_rotate_attribute(
            primary_axis
        )

        if not cmds.attributeQuery(
            "radiusRoll",
            node=switch_ctrl,
            exists=True
        ):
            cmds.addAttr(
                switch_ctrl,
                longName="radiusRoll",
                niceName="Radius Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(radius_roll_joint) + "_radius_roll_md"
        )

        # Wrist roll primary-axis rotation drives input1X.
        cmds.connectAttr(
            wrist_roll_joint + "." + rotate_attr,
            multiply_node + ".input1X",
            force=True
        )

        # Animator multiplier drives input2X.
        cmds.connectAttr(
            switch_ctrl + ".radiusRoll",
            multiply_node + ".input2X",
            force=True
        )

        # Result drives the midpoint forearm roll.
        cmds.connectAttr(
            multiply_node + ".outputX",
            radius_roll_joint + "." + rotate_attr,
            force=True
        )

        print(
            "Created Radius Roll Setup:",
            wrist_roll_joint + "." + rotate_attr,
            "->",
            multiply_node,
            "->",
            radius_roll_joint + "." + rotate_attr
        )

        return multiply_node

    def connect_stretch_roll_midpoint(
        self,
        original_child_joint,
        stretch_joint,
        roll_joint,
        primary_axis,
        node_name
    ):
        translate_attr = self.primary_translate_attribute(
            primary_axis
        )

        scale_attr = self.primary_scale_attribute(
            primary_axis
        )

        original_segment_length = cmds.getAttr(
            original_child_joint + "." + translate_attr
        )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=node_name
        )

        cmds.connectAttr(
            stretch_joint + "." + scale_attr,
            multiply_node + ".input1X",
            force=True
        )

        cmds.setAttr(
            multiply_node + ".input2X",
            original_segment_length * 0.5
        )

        cmds.connectAttr(
            multiply_node + ".outputX",
            roll_joint + "." + translate_attr,
            force=True
        )

        print(
            "Connected Roll Midpoint Position:",
            stretch_joint + "." + scale_attr,
            "->",
            multiply_node,
            "->",
            roll_joint + "." + translate_attr
        )

        return multiply_node

    def setup_roll_midpoint_positions(
        self,
        bind_chain,
        ik_chain,
        roll_segments,
        primary_axis
    ):
        if len(bind_chain) < 3 or len(ik_chain) < 3:
            cmds.warning(
                "Roll midpoint setup needs at least three bind and IK joints."
            )
            return []

        if len(roll_segments) < 2:
            cmds.warning(
                "Roll midpoint joints were not created."
            )
            return []

        bicep_roll_joint = roll_segments[0][1]

        bicep_position_node = self.connect_stretch_roll_midpoint(
            bind_chain[1],
            ik_chain[0],
            bicep_roll_joint,
            primary_axis,
            self.short_name(bicep_roll_joint) + "_position_md"
        )

        radius_roll_joint = roll_segments[1][0]

        radius_position_node = self.connect_stretch_roll_midpoint(
            bind_chain[2],
            ik_chain[1],
            radius_roll_joint,
            primary_axis,
            self.short_name(radius_roll_joint) + "_position_md"
        )

        return [
            bicep_position_node,
            radius_position_node
        ]

    def build_roll_placeholder(self, chain):
        print("TODO: Add roll joints for:")
        print("Start:", chain[0])
        print("End:", chain[-1])

    def add_custom_roll_joint(self, *args):
        if (
            not self.custom_roll_start_joint
            or not self.custom_roll_end_joint
        ):
            cmds.warning(
                "Load both Roll Start Joint and Roll End Joint."
            )
            return

        if self.custom_roll_start_joint == self.custom_roll_end_joint:
            cmds.warning(
                "Roll Start Joint and Roll End Joint cannot be the same."
            )
            return

        roll_chain = self.get_chain_between(
            self.custom_roll_start_joint,
            self.custom_roll_end_joint
        )

        if len(roll_chain) < 2:
            cmds.warning(
                "Roll Start and End must belong to one connected joint chain."
            )
            return

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

        if primary_axis == secondary_axis:
            cmds.warning(
                "Primary Axis and Secondary Axis cannot be the same."
            )
            return

        roll_mode = cmds.optionMenu(
            self.custom_roll_mode_menu,
            query=True,
            value=True
        )

        if roll_mode == "Upper Segment Roll":
            self.build_custom_upper_roll(
                self.custom_roll_start_joint,
                self.custom_roll_end_joint,
                primary_axis,
                secondary_axis
            )
        else:
            self.build_custom_lower_roll(
                self.custom_roll_start_joint,
                self.custom_roll_end_joint,
                primary_axis,
                secondary_axis
            )

        cmds.confirmDialog(
            title="Done",
            message="Custom Roll Joint added.",
            button=["OK"]
        )

    def load_custom_roll_start_joint(self, *args):
        joint = self.selected_joint()
        if not joint:
            return

        self.custom_roll_start_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_roll_start_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Custom Roll Start Joint:", joint)

    def load_custom_roll_end_joint(self, *args):
        joint = self.selected_joint()
        if not joint:
            return

        self.custom_roll_end_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_roll_end_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Custom Roll End Joint:", joint)

    def build_custom_upper_roll(
        self,
        start_joint,
        end_joint,
        primary_axis,
        secondary_axis
    ):
        segment_name = self.short_name(start_joint) + "_custom_upper"
        roll_segment = self.create_simple_roll_segment(
            start_joint,
            end_joint,
            segment_name
        )

        locator = self.create_secondary_locator(
            start_joint,
            secondary_axis,
            segment_name + "_roll_aim_loc"
        )

        aim_vector = self.primary_axis_vector(primary_axis)
        secondary_vector = self.secondary_axis_vector(secondary_axis)
        up_vector = tuple(-v for v in secondary_vector)

        cmds.aimConstraint(
            end_joint,
            roll_segment[0],
            maintainOffset=False,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=locator
        )

        self.create_upper_roll_follow_chain(
            roll_segment,
            locator,
            end_joint,
            secondary_axis,
            distance=2.0
        )

        return roll_segment

    def build_custom_lower_roll(
        self,
        start_joint,
        end_joint,
        primary_axis,
        secondary_axis
    ):
        roll_segment = self.create_forearm_roll_joints(
            start_joint,
            end_joint
        )
        midpoint_roll, end_roll = roll_segment

        locator = self.create_secondary_locator(
            end_roll,
            secondary_axis,
            self.short_name(end_joint) + "_custom_lower_roll_aim_loc"
        )
        cmds.parent(locator, end_joint)

        aim_vector = self.primary_axis_vector(primary_axis)
        reverse_aim = tuple(-v for v in aim_vector)
        secondary_vector = self.secondary_axis_vector(secondary_axis)
        up_vector = tuple(-v for v in secondary_vector)

        cmds.aimConstraint(
            start_joint,
            end_roll,
            maintainOffset=False,
            aimVector=reverse_aim,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=locator
        )

        rotate_attr = self.primary_rotate_attribute(primary_axis)
        if not cmds.attributeQuery("customRoll", node=end_joint, exists=True):
            cmds.addAttr(
                end_joint,
                longName="customRoll",
                niceName="Custom Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        md = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(midpoint_roll) + "_custom_roll_md"
        )
        cmds.connectAttr(end_roll + "." + rotate_attr, md + ".input1X", force=True)
        cmds.connectAttr(end_joint + ".customRoll", md + ".input2X", force=True)
        cmds.connectAttr(md + ".outputX", midpoint_roll + "." + rotate_attr, force=True)

        return roll_segment
"""Maya auto-limb builder module."""

import maya.cmds as cmds


class RollMixin(object):
    def create_secondary_locator(
        self,
        joint,
        secondary_axis,
        name,
        distance=4.0
    ):
        locator = cmds.spaceLocator(
            name=name
        )[0]

        # Temporarily align position and orientation to the joint.
        temp_constraint = cmds.parentConstraint(
            joint,
            locator,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Move in the opposite direction of the selected secondary axis.
        cmds.move(
            -secondary_vector[0] * distance,
            -secondary_vector[1] * distance,
            -secondary_vector[2] * distance,
            locator,
            relative=True,
            objectSpace=True
        )

        return locator

    def create_roll_aim_locators(
        self,
        bind_chain,
        roll_segments,
        secondary_axis,
        rig_type
    ):
        if len(bind_chain) < 3 or len(roll_segments) < 2:
            cmds.warning(
                "Roll aim locators need three main joints and two roll segments."
            )
            return []

        if rig_type == "Arm":
            first_locator_name = "humerus_roll_aim_loc"
            second_locator_name = "elbow_roll_aim_loc"

        else:
            first_locator_name = "femur_roll_aim_loc"
            second_locator_name = "knee_roll_aim_loc"

        # First locator starts from the main root joint.
        first_locator = self.create_secondary_locator(
            bind_chain[0],
            secondary_axis,
            first_locator_name
        )

        # The lower segment has no roll root.
        # Use the wrist/end roll joint as the second locator source.
        wrist_roll_joint = roll_segments[1][1]

        second_locator = self.create_secondary_locator(
            wrist_roll_joint,
            secondary_axis,
            second_locator_name
        )

        # Parent the wrist aim locator under the last main joint (wrist/ankle).
        cmds.parent(
            second_locator,
            bind_chain[2]
        )

        print(
            "Created Roll Aim Locators:",
            first_locator,
            second_locator
        )

        return [
            first_locator,
            second_locator
        ]

    def duplicate_joint_only(self, source_joint, new_name):
        new_joint = cmds.duplicate(
            source_joint,
            parentOnly=True,
            name=new_name
        )[0]

        parent = cmds.listRelatives(
            new_joint,
            parent=True,
            fullPath=True
        ) or []

        if parent:
            new_joint = cmds.parent(
                new_joint,
                world=True
            )[0]

        return new_joint

    def create_simple_roll_segment(
        self,
        start_joint,
        end_joint,
        segment_name
    ):
        roll_root = self.duplicate_joint_only(
            start_joint,
            segment_name + "_roll_root_jnt"
        )

        temp_constraint = cmds.parentConstraint(
            start_joint,
            roll_root,
            maintainOffset=False
        )[0]
        cmds.delete(temp_constraint)

        roll_root = cmds.parent(
            roll_root,
            start_joint
        )[0]

        roll_mid = self.duplicate_joint_only(
            start_joint,
            segment_name + "_roll_mid_jnt"
        )

        start_position = cmds.xform(
            start_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        end_position = cmds.xform(
            end_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        midpoint = [
            (start_position[0] + end_position[0]) * 0.5,
            (start_position[1] + end_position[1]) * 0.5,
            (start_position[2] + end_position[2]) * 0.5
        ]

        cmds.xform(
            roll_mid,
            worldSpace=True,
            translation=midpoint
        )

        roll_mid = cmds.parent(
            roll_mid,
            roll_root
        )[0]

        print(
            "Created Roll Segment:",
            roll_root,
            roll_mid
        )

        return roll_root, roll_mid

    def create_forearm_roll_joints(
        self,
        elbow_joint,
        wrist_joint
    ):
        elbow_name = self.short_name(elbow_joint)
        wrist_name = self.short_name(wrist_joint)

        elbow_position = cmds.xform(
            elbow_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        wrist_position = cmds.xform(
            wrist_joint,
            query=True,
            worldSpace=True,
            translation=True
        )

        midpoint = [
            (elbow_position[0] + wrist_position[0]) * 0.5,
            (elbow_position[1] + wrist_position[1]) * 0.5,
            (elbow_position[2] + wrist_position[2]) * 0.5
        ]

        # Joint in the middle of the forearm.
        forearm_mid_roll = self.duplicate_joint_only(
            elbow_joint,
            elbow_name + "_forearm_mid_roll_jnt"
        )

        cmds.xform(
            forearm_mid_roll,
            worldSpace=True,
            translation=midpoint
        )

        forearm_mid_roll = cmds.parent(
            forearm_mid_roll,
            elbow_joint
        )[0]

        # Joint at the wrist position.
        wrist_roll = self.duplicate_joint_only(
            wrist_joint,
            wrist_name + "_roll_jnt"
        )

        temp_constraint = cmds.parentConstraint(
            wrist_joint,
            wrist_roll,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        wrist_roll = cmds.parent(
            wrist_roll,
            elbow_joint
        )[0]

        # These two roll joints are siblings.
        # Both are children of the main elbow joint.
        print(
            "Created Forearm Roll Joints:",
            forearm_mid_roll,
            wrist_roll,
            "Parent:",
            elbow_joint
        )

        return forearm_mid_roll, wrist_roll

    def rotate_order_primary_last(self, primary_axis):
        rotate_order_map = {
            "X": 1,  # YZX: X is last
            "Y": 3,  # XZY: Y is last
            "Z": 0   # XYZ: Z is last
        }

        return rotate_order_map.get(
            primary_axis,
            1
        )

    def set_roll_joint_rotate_orders(
        self,
        roll_segments,
        primary_axis
    ):
        rotate_order = self.rotate_order_primary_last(
            primary_axis
        )

        for segment in roll_segments:
            for roll_joint in segment:
                if cmds.objExists(roll_joint):
                    cmds.setAttr(
                        roll_joint + ".rotateOrder",
                        rotate_order
                    )

        print(
            "Set Roll Joint Rotate Order:",
            primary_axis,
            "last"
        )

    def build_simple_roll_joints(self, bind_chain):
        if len(bind_chain) < 3:
            cmds.warning(
                "Simple roll setup needs at least 3 joints."
            )
            return []

        first_name = self.short_name(bind_chain[0])

        # Upper segment remains a root + midpoint chain.
        first_segment = self.create_simple_roll_segment(
            bind_chain[0],
            bind_chain[1],
            first_name
        )

        # Lower segment has two sibling roll joints:
        # one at the midpoint and one at the wrist/end joint.
        second_segment = self.create_forearm_roll_joints(
            bind_chain[1],
            bind_chain[2]
        )

        print(
            "Created Roll Joints:",
            first_segment,
            second_segment
        )

        return [
            first_segment,
            second_segment
        ]

    def aim_simple_roll_segments(
        self,
        bind_chain,
        roll_segments,
        aim_locators,
        primary_axis,
        secondary_axis,
        rig_type
    ):
        if len(bind_chain) < 3:
            return

        if len(roll_segments) < 2 or len(aim_locators) < 2:
            return

        aim_vector = self.primary_axis_vector(
            primary_axis
        )

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Aim Constraint uses the opposite direction of Secondary Axis.
        up_vector = (
            -secondary_vector[0],
            -secondary_vector[1],
            -secondary_vector[2]
        )

        first_roll_root = roll_segments[0][0]

        # Lower segment:
        # [0] = forearm midpoint roll
        # [1] = wrist roll
        wrist_roll_joint = roll_segments[1][1]

        # Upper roll root aims toward elbow/knee.
        cmds.aimConstraint(
            bind_chain[1],
            first_roll_root,
            maintainOffset=False,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=aim_locators[0]
        )

        # Wrist roll aims backward toward elbow/knee.
        reverse_aim_vector = (
            -aim_vector[0],
            -aim_vector[1],
            -aim_vector[2]
        )

        # Arm wrist roll: maintainOffset=False
        # Leg ankle roll: maintainOffset=True
        keep_end_offset = rig_type == "Leg"

        cmds.aimConstraint(
            bind_chain[1],
            wrist_roll_joint,
            maintainOffset=keep_end_offset,
            aimVector=reverse_aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=aim_locators[1]
        )

        print(
            "Created Roll Aim Constraints:",
            first_roll_root,
            "->",
            bind_chain[1],
            wrist_roll_joint,
            "->",
            bind_chain[1]
        )

    def create_upper_roll_follow_chain(
        self,
        first_roll_segment,
        upper_aim_locator,
        target_joint,
        secondary_axis,
        distance=2.0
    ):
        roll_root = first_roll_segment[0]
        roll_mid = first_roll_segment[1]

        root_name = self.short_name(roll_root)
        mid_name = self.short_name(roll_mid)

        follow_root = self.duplicate_joint_only(
            roll_root,
            root_name.replace("_jnt", "") + "_follow_jnt"
        )

        follow_mid = self.duplicate_joint_only(
            roll_mid,
            mid_name.replace("_jnt", "") + "_follow_jnt"
        )

        # Make a clean follow hierarchy.
        follow_mid = cmds.parent(
            follow_mid,
            follow_root
        )[0]

        secondary_vector = self.secondary_axis_vector(
            secondary_axis
        )

        # Move the follow chain in the same opposite-secondary direction
        # as the locator, but only halfway, so it sits between the
        # original roll joints and the locator.
        cmds.move(
            -secondary_vector[0] * distance,
            -secondary_vector[1] * distance,
            -secondary_vector[2] * distance,
            follow_root,
            relative=True,
            objectSpace=True
        )

        # Parent the upper-arm aim locator under the follow root.
        # Maya keeps its world position by default.
        cmds.parent(
            upper_aim_locator,
            follow_root
        )

        follow_ikh = cmds.ikHandle(
            name=root_name.replace("_jnt", "") + "_follow_ikh",
            startJoint=follow_root,
            endEffector=follow_mid,
            solver="ikRPsolver"
        )[0]

        # Zero the IK Handle pole vector values.
        for axis in "XYZ":
            pole_attr = follow_ikh + ".poleVector" + axis

            if cmds.objExists(pole_attr):
                cmds.setAttr(
                    pole_attr,
                    0
                )

        # Snap the IK Handle to the second main joint.
        temp_constraint = cmds.pointConstraint(
            target_joint,
            follow_ikh,
            maintainOffset=False
        )[0]

        cmds.delete(temp_constraint)

        # Parent the IK Handle under the second main joint.
        follow_ikh = cmds.parent(
            follow_ikh,
            target_joint
        )[0]

        print(
            "Created Upper Roll Follow Chain:",
            follow_root,
            follow_mid,
            follow_ikh
        )

        return follow_root, follow_mid, follow_ikh

    def setup_bicep_roll(
        self,
        bind_chain,
        first_roll_segment,
        switch_ctrl,
        primary_axis
    ):
        if len(bind_chain) < 2:
            cmds.warning(
                "Bicep roll needs at least two main joints."
            )
            return None

        if not first_roll_segment:
            cmds.warning(
                "Upper roll segment was not created."
            )
            return None

        humerus_joint = bind_chain[0]

        # first_roll_segment:
        # [0] = humerus roll root
        # [1] = bicep roll midpoint joint
        bicep_roll_joint = first_roll_segment[1]

        rotate_attr = self.primary_rotate_attribute(
            primary_axis
        )

        if not cmds.attributeQuery(
            "bicepRoll",
            node=switch_ctrl,
            exists=True
        ):
            cmds.addAttr(
                switch_ctrl,
                longName="bicepRoll",
                niceName="Bicep Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(humerus_joint) + "_bicep_roll_md"
        )

        # Humerus primary-axis rotation drives input1X.
        cmds.connectAttr(
            humerus_joint + "." + rotate_attr,
            multiply_node + ".input1X",
            force=True
        )

        # Animator multiplier drives input2X.
        cmds.connectAttr(
            switch_ctrl + ".bicepRoll",
            multiply_node + ".input2X",
            force=True
        )

        # Result drives bicep roll primary-axis rotation.
        cmds.connectAttr(
            multiply_node + ".outputX",
            bicep_roll_joint + "." + rotate_attr,
            force=True
        )

        print(
            "Created Bicep Roll Setup:",
            humerus_joint + "." + rotate_attr,
            "->",
            multiply_node,
            "->",
            bicep_roll_joint + "." + rotate_attr
        )

        return multiply_node

    def setup_radius_roll(
        self,
        second_roll_segment,
        switch_ctrl,
        primary_axis
    ):
        if not second_roll_segment:
            cmds.warning(
                "Forearm roll joints were not created."
            )
            return None

        # second_roll_segment:
        # [0] = midpoint forearm/radius roll
        # [1] = wrist roll
        radius_roll_joint = second_roll_segment[0]
        wrist_roll_joint = second_roll_segment[1]

        rotate_attr = self.primary_rotate_attribute(
            primary_axis
        )

        if not cmds.attributeQuery(
            "radiusRoll",
            node=switch_ctrl,
            exists=True
        ):
            cmds.addAttr(
                switch_ctrl,
                longName="radiusRoll",
                niceName="Radius Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(radius_roll_joint) + "_radius_roll_md"
        )

        # Wrist roll primary-axis rotation drives input1X.
        cmds.connectAttr(
            wrist_roll_joint + "." + rotate_attr,
            multiply_node + ".input1X",
            force=True
        )

        # Animator multiplier drives input2X.
        cmds.connectAttr(
            switch_ctrl + ".radiusRoll",
            multiply_node + ".input2X",
            force=True
        )

        # Result drives the midpoint forearm roll.
        cmds.connectAttr(
            multiply_node + ".outputX",
            radius_roll_joint + "." + rotate_attr,
            force=True
        )

        print(
            "Created Radius Roll Setup:",
            wrist_roll_joint + "." + rotate_attr,
            "->",
            multiply_node,
            "->",
            radius_roll_joint + "." + rotate_attr
        )

        return multiply_node

    def connect_stretch_roll_midpoint(
        self,
        original_child_joint,
        stretch_joint,
        roll_joint,
        primary_axis,
        node_name
    ):
        translate_attr = self.primary_translate_attribute(
            primary_axis
        )

        scale_attr = self.primary_scale_attribute(
            primary_axis
        )

        original_segment_length = cmds.getAttr(
            original_child_joint + "." + translate_attr
        )

        multiply_node = cmds.createNode(
            "multiplyDivide",
            name=node_name
        )

        cmds.connectAttr(
            stretch_joint + "." + scale_attr,
            multiply_node + ".input1X",
            force=True
        )

        cmds.setAttr(
            multiply_node + ".input2X",
            original_segment_length * 0.5
        )

        cmds.connectAttr(
            multiply_node + ".outputX",
            roll_joint + "." + translate_attr,
            force=True
        )

        print(
            "Connected Roll Midpoint Position:",
            stretch_joint + "." + scale_attr,
            "->",
            multiply_node,
            "->",
            roll_joint + "." + translate_attr
        )

        return multiply_node

    def setup_roll_midpoint_positions(
        self,
        bind_chain,
        ik_chain,
        roll_segments,
        primary_axis
    ):
        if len(bind_chain) < 3 or len(ik_chain) < 3:
            cmds.warning(
                "Roll midpoint setup needs at least three bind and IK joints."
            )
            return []

        if len(roll_segments) < 2:
            cmds.warning(
                "Roll midpoint joints were not created."
            )
            return []

        bicep_roll_joint = roll_segments[0][1]

        bicep_position_node = self.connect_stretch_roll_midpoint(
            bind_chain[1],
            ik_chain[0],
            bicep_roll_joint,
            primary_axis,
            self.short_name(bicep_roll_joint) + "_position_md"
        )

        radius_roll_joint = roll_segments[1][0]

        radius_position_node = self.connect_stretch_roll_midpoint(
            bind_chain[2],
            ik_chain[1],
            radius_roll_joint,
            primary_axis,
            self.short_name(radius_roll_joint) + "_position_md"
        )

        return [
            bicep_position_node,
            radius_position_node
        ]

    def build_roll_placeholder(self, chain):
        print("TODO: Add roll joints for:")
        print("Start:", chain[0])
        print("End:", chain[-1])

    def add_custom_roll_joint(self, *args):
        if (
            not self.custom_roll_start_joint
            or not self.custom_roll_end_joint
        ):
            cmds.warning(
                "Load both Roll Start Joint and Roll End Joint."
            )
            return

        if self.custom_roll_start_joint == self.custom_roll_end_joint:
            cmds.warning(
                "Roll Start Joint and Roll End Joint cannot be the same."
            )
            return

        roll_chain = self.get_chain_between(
            self.custom_roll_start_joint,
            self.custom_roll_end_joint
        )

        if len(roll_chain) < 2:
            cmds.warning(
                "Roll Start and End must belong to one connected joint chain."
            )
            return

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

        if primary_axis == secondary_axis:
            cmds.warning(
                "Primary Axis and Secondary Axis cannot be the same."
            )
            return

        roll_mode = cmds.optionMenu(
            self.custom_roll_mode_menu,
            query=True,
            value=True
        )

        if roll_mode == "Upper Segment Roll":
            self.build_custom_upper_roll(
                self.custom_roll_start_joint,
                self.custom_roll_end_joint,
                primary_axis,
                secondary_axis
            )
        else:
            self.build_custom_lower_roll(
                self.custom_roll_start_joint,
                self.custom_roll_end_joint,
                primary_axis,
                secondary_axis
            )

        cmds.confirmDialog(
            title="Done",
            message="Custom Roll Joint added.",
            button=["OK"]
        )

    def load_custom_roll_start_joint(self, *args):
        joint = self.selected_joint()
        if not joint:
            return

        self.custom_roll_start_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_roll_start_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Custom Roll Start Joint:", joint)

    def load_custom_roll_end_joint(self, *args):
        joint = self.selected_joint()
        if not joint:
            return

        self.custom_roll_end_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_roll_end_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Custom Roll End Joint:", joint)

    def build_custom_upper_roll(
        self,
        start_joint,
        end_joint,
        primary_axis,
        secondary_axis
    ):
        segment_name = self.short_name(start_joint) + "_custom_upper"
        roll_segment = self.create_simple_roll_segment(
            start_joint,
            end_joint,
            segment_name
        )

        locator = self.create_secondary_locator(
            start_joint,
            secondary_axis,
            segment_name + "_roll_aim_loc"
        )

        aim_vector = self.primary_axis_vector(primary_axis)
        secondary_vector = self.secondary_axis_vector(secondary_axis)
        up_vector = tuple(-v for v in secondary_vector)

        cmds.aimConstraint(
            end_joint,
            roll_segment[0],
            maintainOffset=False,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=locator
        )

        self.create_upper_roll_follow_chain(
            roll_segment,
            locator,
            end_joint,
            secondary_axis,
            distance=2.0
        )

        return roll_segment

    def build_custom_lower_roll(
        self,
        start_joint,
        end_joint,
        primary_axis,
        secondary_axis
    ):
        roll_segment = self.create_forearm_roll_joints(
            start_joint,
            end_joint
        )
        midpoint_roll, end_roll = roll_segment

        locator = self.create_secondary_locator(
            end_roll,
            secondary_axis,
            self.short_name(end_joint) + "_custom_lower_roll_aim_loc"
        )
        cmds.parent(locator, end_joint)

        aim_vector = self.primary_axis_vector(primary_axis)
        reverse_aim = tuple(-v for v in aim_vector)
        secondary_vector = self.secondary_axis_vector(secondary_axis)
        up_vector = tuple(-v for v in secondary_vector)

        cmds.aimConstraint(
            start_joint,
            end_roll,
            maintainOffset=False,
            aimVector=reverse_aim,
            upVector=up_vector,
            worldUpType="object",
            worldUpObject=locator
        )

        rotate_attr = self.primary_rotate_attribute(primary_axis)
        if not cmds.attributeQuery("customRoll", node=end_joint, exists=True):
            cmds.addAttr(
                end_joint,
                longName="customRoll",
                niceName="Custom Roll",
                attributeType="double",
                defaultValue=1.0,
                keyable=True
            )

        md = cmds.createNode(
            "multiplyDivide",
            name=self.short_name(midpoint_roll) + "_custom_roll_md"
        )
        cmds.connectAttr(end_roll + "." + rotate_attr, md + ".input1X", force=True)
        cmds.connectAttr(end_joint + ".customRoll", md + ".input2X", force=True)
        cmds.connectAttr(md + ".outputX", midpoint_roll + "." + rotate_attr, force=True)

        return roll_segment
