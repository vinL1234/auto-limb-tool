"""Maya auto-limb builder module."""

import maya.cmds as cmds


class StretchMixin(object):
    def create_stretch_start_locator(self, ik_root_joint):
        locator = cmds.spaceLocator(
            name=self.short_name(ik_root_joint) + "_stretch_start_loc"
        )[0]

        temp_constraint = cmds.parentConstraint(
            ik_root_joint,
            locator,
            maintainOffset=False
        )[0]
        cmds.delete(temp_constraint)

        ik_root_parent = cmds.listRelatives(
            ik_root_joint,
            parent=True,
            fullPath=True
        ) or []

        if ik_root_parent:
            locator = cmds.parent(
                locator,
                ik_root_parent[0]
            )[0]

        print("Created Stretch Start Locator:", locator)
        return locator

    def build_ik_stretch(
        self,
        ik_chain,
        ik_ctrl,
        switch_ctrl,
        primary_axis
    ):
        if len(ik_chain) < 3:
            cmds.warning(
                "IK Stretch needs at least three joints."
            )
            return None

        translate_attr = self.primary_translate_attribute(
            primary_axis
        )

        scale_attr = self.primary_scale_attribute(
            primary_axis
        )

        # The child joint translation stores the length
        # of the segment above it.
        upper_length = abs(
            cmds.getAttr(
                ik_chain[1] + "." + translate_attr
            )
        )

        lower_length = abs(
            cmds.getAttr(
                ik_chain[2] + "." + translate_attr
            )
        )

        original_length = upper_length + lower_length

        if original_length <= 0.0001:
            cmds.warning(
                "Cannot create stretch because original limb length is zero."
            )
            return None

        root_name = self.short_name(
            ik_chain[0]
        )

        # Measure the current world-space distance
        # from IK root to IK wrist/ankle control.
        distance_node = cmds.createNode(
            "distanceBetween",
            name=root_name + "_stretch_distance"
        )

        stretch_start_locator = self.create_stretch_start_locator(
            ik_chain[0]
        )

        cmds.connectAttr(
            stretch_start_locator + ".worldMatrix[0]",
            distance_node + ".inMatrix1",
            force=True
        )

        cmds.connectAttr(
            ik_ctrl + ".worldMatrix[0]",
            distance_node + ".inMatrix2",
            force=True
        )

        # stretch ratio = current distance / original length
        ratio_node = cmds.createNode(
            "multiplyDivide",
            name=root_name + "_stretch_ratio_md"
        )

        # 2 = Divide
        cmds.setAttr(
            ratio_node + ".operation",
            2
        )

        cmds.connectAttr(
            distance_node + ".distance",
            ratio_node + ".input1X",
            force=True
        )

        cmds.setAttr(
            ratio_node + ".input2X",
            original_length
        )

        # Do not allow squash.
        # If ratio > 1, output ratio.
        # Otherwise output 1.
        condition_node = cmds.createNode(
            "condition",
            name=root_name + "_stretch_condition"
        )

        # 2 = Greater Than
        cmds.setAttr(
            condition_node + ".operation",
            2
        )

        cmds.connectAttr(
            ratio_node + ".outputX",
            condition_node + ".firstTerm",
            force=True
        )

        cmds.setAttr(
            condition_node + ".secondTerm",
            1.0
        )

        cmds.connectAttr(
            ratio_node + ".outputX",
            condition_node + ".colorIfTrueR",
            force=True
        )

        cmds.setAttr(
            condition_node + ".colorIfFalseR",
            1.0
        )

        # Enable stretch only in IK mode.
        # blendColors:
        # blender = 1 -> color1
        # blender = 0 -> color2
        ik_blend = cmds.createNode(
            "blendColors",
            name=root_name + "_stretch_ik_blend"
        )

        # IK mode output.
        cmds.connectAttr(
            condition_node + ".outColorR",
            ik_blend + ".color1R",
            force=True
        )

        # FK mode output.
        cmds.setAttr(
            ik_blend + ".color2R",
            1.0
        )

        cmds.connectAttr(
            switch_ctrl + ".ikFk",
            ik_blend + ".blender",
            force=True
        )

        # Stretch only the first and second IK joints.
        # Joint 3 is the end joint and does not need scale.
        cmds.connectAttr(
            ik_blend + ".outputR",
            ik_chain[0] + "." + scale_attr,
            force=True
        )

        cmds.connectAttr(
            ik_blend + ".outputR",
            ik_chain[1] + "." + scale_attr,
            force=True
        )

        print("Created IK Stretch")
        print("Original limb length:", original_length)
        print("Upper segment length:", upper_length)
        print("Lower segment length:", lower_length)
        print("Stretch scale attribute:", scale_attr)

        return {
            "stretch_start_locator": stretch_start_locator,
            "distance_node": distance_node,
            "ratio_node": ratio_node,
            "condition_node": condition_node,
            "ik_blend": ik_blend,
            "original_length": original_length
        }

    def load_custom_stretch_control(self, *args):
        selection = cmds.ls(
            selection=True,
            transforms=True,
            long=True
        ) or []

        if len(selection) != 1:
            cmds.warning("Please select exactly one transform control.")
            return

        ctrl = selection[0]
        shapes = cmds.listRelatives(
            ctrl,
            shapes=True,
            fullPath=True
        ) or []

        if not shapes:
            cmds.warning("Selected transform does not have a shape.")
            return

        self.custom_stretch_ctrl = ctrl

        if self.custom_stretch_ctrl_field:
            cmds.textFieldButtonGrp(
                self.custom_stretch_ctrl_field,
                edit=True,
                text=self.short_name(ctrl)
            )

    def update_custom_stretch_ui(self, *args):
        if not self.custom_stretch_mode_menu:
            return

        mode = cmds.optionMenu(
            self.custom_stretch_mode_menu,
            query=True,
            value=True
        )

        cmds.textFieldButtonGrp(
            self.custom_stretch_ctrl_field,
            edit=True,
            enable=(mode == "Use Selected Control")
        )

    def create_custom_ik_control(self, ik_chain, ik_handle):
        end_joint = ik_chain[-1]
        ctrl = self.create_square_ctrl(
            self.short_name(end_joint) + "_custom_IK_ctrl",
            size=1.8
        )
        offset = cmds.group(ctrl, name=ctrl + "_offset")
        self.match_group_to_object(offset, end_joint)
        cmds.parentConstraint(ctrl, ik_handle, maintainOffset=True)
        cmds.orientConstraint(ctrl, end_joint, maintainOffset=True)
        return ctrl

    def connect_existing_custom_control(self, ctrl, ik_chain, ik_handle):
        cmds.parentConstraint(ctrl, ik_handle, maintainOffset=True)
        cmds.orientConstraint(ctrl, ik_chain[-1], maintainOffset=True)

    def build_custom_stretch(self, ik_chain, ik_ctrl, primary_axis):
        if len(ik_chain) < 2:
            cmds.warning("Custom Stretch needs at least two IK joints.")
            return None

        translate_attr = self.primary_translate_attribute(primary_axis)
        scale_attr = self.primary_scale_attribute(primary_axis)

        original_length = 0.0
        for child_joint in ik_chain[1:]:
            original_length += abs(
                cmds.getAttr(child_joint + "." + translate_attr)
            )

        if original_length <= 0.0001:
            cmds.warning("Custom chain original length is zero.")
            return None

        if not cmds.attributeQuery("stretchiness", node=ik_ctrl, exists=True):
            cmds.addAttr(
                ik_ctrl,
                longName="stretchiness",
                niceName="Stretchiness",
                attributeType="double",
                minValue=0.0,
                maxValue=1.0,
                defaultValue=1.0,
                keyable=True
            )

        start_locator = self.create_stretch_start_locator(ik_chain[0])
        root_name = self.short_name(ik_chain[0])

        distance_node = cmds.createNode(
            "distanceBetween",
            name=root_name + "_custom_stretch_distance"
        )
        cmds.connectAttr(start_locator + ".worldMatrix[0]", distance_node + ".inMatrix1", force=True)
        cmds.connectAttr(ik_ctrl + ".worldMatrix[0]", distance_node + ".inMatrix2", force=True)

        ratio_node = cmds.createNode(
            "multiplyDivide",
            name=root_name + "_custom_stretch_ratio_md"
        )
        cmds.setAttr(ratio_node + ".operation", 2)
        cmds.connectAttr(distance_node + ".distance", ratio_node + ".input1X", force=True)
        cmds.setAttr(ratio_node + ".input2X", original_length)

        condition_node = cmds.createNode(
            "condition",
            name=root_name + "_custom_stretch_condition"
        )
        cmds.setAttr(condition_node + ".operation", 2)
        cmds.connectAttr(ratio_node + ".outputX", condition_node + ".firstTerm", force=True)
        cmds.setAttr(condition_node + ".secondTerm", 1.0)
        cmds.connectAttr(ratio_node + ".outputX", condition_node + ".colorIfTrueR", force=True)
        cmds.setAttr(condition_node + ".colorIfFalseR", 1.0)

        stretch_blend = cmds.createNode(
            "blendColors",
            name=root_name + "_custom_stretchiness_blend"
        )
        cmds.connectAttr(condition_node + ".outColorR", stretch_blend + ".color1R", force=True)
        cmds.setAttr(stretch_blend + ".color2R", 1.0)
        cmds.connectAttr(ik_ctrl + ".stretchiness", stretch_blend + ".blender", force=True)

        for ik_joint in ik_chain[:-1]:
            cmds.connectAttr(
                stretch_blend + ".outputR",
                ik_joint + "." + scale_attr,
                force=True
            )

        return {
            "start_locator": start_locator,
            "distance": distance_node,
            "ratio": ratio_node,
            "condition": condition_node,
            "blend": stretch_blend,
            "output": stretch_blend + ".outputR"
        }

    def load_custom_stretch_start_joint(self, *args):
        joint = self.selected_joint()

        if not joint:
            return

        self.custom_stretch_start_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_stretch_start_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Stretch Start Joint:", joint)

    def load_custom_stretch_end_joint(self, *args):
        joint = self.selected_joint()

        if not joint:
            return

        self.custom_stretch_end_joint = joint

        cmds.textFieldButtonGrp(
            self.custom_stretch_end_field,
            edit=True,
            text=self.short_name(joint)
        )

        print("Loaded Stretch End Joint:", joint)

    def add_custom_stretch(self, *args):
        if (
            not self.custom_stretch_start_joint
            or not self.custom_stretch_end_joint
        ):
            cmds.warning(
                "Load both Stretch Start Joint and Stretch End Joint."
            )
            return

        if not self.custom_stretch_ctrl:
            cmds.warning(
                "Load the IK control used as the Stretch target."
            )
            return

        primary_axis = cmds.optionMenu(
            self.custom_primary_axis_menu,
            query=True,
            value=True
        )

        stretch_chain = self.get_chain_between(
            self.custom_stretch_start_joint,
            self.custom_stretch_end_joint
        )

        if len(stretch_chain) < 2:
            cmds.warning(
                "Stretch Start and End must belong to one connected joint chain."
            )
            return

        self.build_custom_stretch(
            stretch_chain,
            self.custom_stretch_ctrl,
            primary_axis
        )

        cmds.confirmDialog(
            title="Done",
            message="Custom Stretch added.",
            button=["OK"]
        )
