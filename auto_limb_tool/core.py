"""Maya auto-limb builder module."""

import maya.cmds as cmds


# Shared helpers for joint selection, traversal, duplication, and axis mapping.
class CoreMixin(object):
    def short_name(self, obj):
        return obj.split("|")[-1]

    def selected_joint(self):
        # Use long=True to avoid "More than one object matches name" 
        sel = cmds.ls(selection=True, type="joint", long=True)
        if not sel:
            cmds.warning("Please select a joint.")
            return None
        return sel[0]

    def get_joint_chain(self, root):
        children = cmds.listRelatives(
            root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        children.reverse()
        return [root] + children

    def get_first_child_chain(self, root):
        """
        Get a clean chain by following the first child joint.
        Good for arm/leg/tail style chains.
        """
        chain = [root]
        current = root

        while True:
            children = cmds.listRelatives(
                current,
                children=True,
                type="joint",
                fullPath=True
            ) or []

            if not children:
                break

            current = children[0]
            chain.append(current)

        return chain

    def get_chain_between(self, start, end):
        """
        Get a chain from start joint to end joint.
        This assumes start and end are in self.custom_chain or same hierarchy.
        """
        chain = [start]
        current = start

        while current != end:
            children = cmds.listRelatives(
                current,
                children=True,
                type="joint",
                fullPath=True
            ) or []

            if not children:
                cmds.warning("End joint is not under start joint.")
                return []

            current = children[0]
            chain.append(current)

            if len(chain) > 100:
                cmds.warning("Invalid chain.")
                return []

        return chain

    def clean_duplicate_name(self, name):
        """
        Maya duplicate often adds a number, like l_humerus1.
        This removes only the duplicate number at the end.
        """
        while name and name[-1].isdigit():
            name = name[:-1]
        return name

    def duplicate_chain(self, root_joint, suffix):
        # Duplicate the full hierarchy and rename it from children to root.
        dup_root = cmds.duplicate(root_joint, renameChildren=True)[0]

        dup_root = (cmds.ls(
            dup_root,
            long=True,
            type="joint"
        ) or [dup_root])[0]

        dup_joints = cmds.listRelatives(
            dup_root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        dup_joints.append(dup_root)

        # Important:
        # Rename deepest children first.
        # If we rename the root first, all child full paths change,

        dup_joints.sort(
            key=lambda x: x.count("|"),
            reverse=True
        )

        renamed_root = None

        for jnt in dup_joints:
            short = self.short_name(jnt)
            short = self.clean_duplicate_name(short)

            # Keep the original name and only add _IK or _FK.
            new_name = short + suffix

            renamed_jnt = cmds.rename(jnt, new_name)

            if jnt == dup_root:
                renamed_root = renamed_jnt

        if not renamed_root:
            cmds.warning("Could not find duplicated root.")
            return []

        renamed_root = (cmds.ls(
            renamed_root,
            long=True,
            type="joint"
        ) or [renamed_root])[0]

        # Return the renamed hierarchy from root to children.
        renamed = cmds.listRelatives(
            renamed_root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        renamed.reverse()
        renamed = [renamed_root] + renamed

        return renamed

    def duplicate_limb_chain(self, source_chain, suffix):
        # Duplicate joints individually so only the requested limb is rebuilt.
        new_chain = []

        for source_jnt in source_chain:
            short = self.short_name(source_jnt)
            new_name = short + suffix

            new_jnt = cmds.duplicate(
                source_jnt,
                parentOnly=True,
                name=new_name
            )[0]


            parent = cmds.listRelatives(
                new_jnt,
                parent=True,
                fullPath=True
            ) or []

            if parent:
                new_jnt = cmds.parent(
                    new_jnt,
                    world=True
                )[0]

            new_chain.append(new_jnt)


        for i in range(1, len(new_chain)):
            new_chain[i] = cmds.parent(
                new_chain[i],
                new_chain[i - 1]
            )[0]

        return new_chain

    def duplicate_custom_range(self, chain, suffix):
        """
        Duplicate only the selected custom range.
        Example:
            l_humerus -> l_radius -> l_wrist
        """
        new_chain = []

        for source_jnt in chain:
            short = self.short_name(source_jnt)

            short = self.clean_duplicate_name(short)

            # Keep the original name and only add _IK or _FK at the end.
            new_name = short + suffix

            new_jnt = cmds.duplicate(
                source_jnt,
                parentOnly=True,
                name=new_name
            )[0]

            parent = cmds.listRelatives(new_jnt, parent=True) or []
            if parent:
                new_jnt = cmds.parent(new_jnt, world=True)[0]

            new_chain.append(new_jnt)

        for i in range(1, len(new_chain)):
            new_chain[i] = cmds.parent(new_chain[i], new_chain[i - 1])[0]

        return new_chain

    def rename_joint(self, jnt, suffix):
        short = self.short_name(jnt)
        short = self.clean_duplicate_name(short)
        return short + suffix

    def match_group_to_object(self, group, target):
        # Use a temporary constraint to copy the target transform.
        temp = cmds.parentConstraint(
            target,
            group,
            maintainOffset=False
        )[0]
        cmds.delete(temp)

    def secondary_axis_vector(self, secondary_axis):
        axis_map = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1)
        }

        return axis_map.get(
            secondary_axis,
            (0, 1, 0)
        )

    def primary_axis_vector(self, primary_axis):
        axis_map = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1)
        }

        return axis_map.get(
            primary_axis,
            (1, 0, 0)
        )

    def primary_rotate_attribute(self, primary_axis):
        attr_map = {
            "X": "rotateX",
            "Y": "rotateY",
            "Z": "rotateZ"
        }

        return attr_map.get(
            primary_axis,
            "rotateX"
        )

    def primary_translate_attribute(self, primary_axis):
        attr_map = {
            "X": "translateX",
            "Y": "translateY",
            "Z": "translateZ"
        }

        return attr_map.get(
            primary_axis,
            "translateX"
        )

    def primary_scale_attribute(self, primary_axis):
        attr_map = {
            "X": "scaleX",
            "Y": "scaleY",
            "Z": "scaleZ"
        }

        return attr_map.get(
            primary_axis,
            "scaleX"
        )
"""Maya auto-limb builder module."""

import maya.cmds as cmds


class CoreMixin(object):
    def short_name(self, obj):
        return obj.split("|")[-1]

    def selected_joint(self):
        # Use long=True to avoid "More than one object matches name" 
        sel = cmds.ls(selection=True, type="joint", long=True)
        if not sel:
            cmds.warning("Please select a joint.")
            return None
        return sel[0]

    def get_joint_chain(self, root):
        children = cmds.listRelatives(
            root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        children.reverse()
        return [root] + children

    def get_first_child_chain(self, root):
        """
        Get a clean chain by following the first child joint.
        Good for arm/leg/tail style chains.
        """
        chain = [root]
        current = root

        while True:
            children = cmds.listRelatives(
                current,
                children=True,
                type="joint",
                fullPath=True
            ) or []

            if not children:
                break

            current = children[0]
            chain.append(current)

        return chain

    def get_chain_between(self, start, end):
        """
        Get a chain from start joint to end joint.
        This assumes start and end are in self.custom_chain or same hierarchy.
        """
        chain = [start]
        current = start

        while current != end:
            children = cmds.listRelatives(
                current,
                children=True,
                type="joint",
                fullPath=True
            ) or []

            if not children:
                cmds.warning("End joint is not under start joint.")
                return []

            current = children[0]
            chain.append(current)

            if len(chain) > 100:
                cmds.warning("Invalid chain.")
                return []

        return chain

    def clean_duplicate_name(self, name):
        """
        Maya duplicate often adds a number, like l_humerus1.
        This removes only the duplicate number at the end.
        """
        while name and name[-1].isdigit():
            name = name[:-1]
        return name

    def duplicate_chain(self, root_joint, suffix):
        dup_root = cmds.duplicate(root_joint, renameChildren=True)[0]

        dup_root = (cmds.ls(
            dup_root,
            long=True,
            type="joint"
        ) or [dup_root])[0]

        dup_joints = cmds.listRelatives(
            dup_root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        dup_joints.append(dup_root)

        # Important:
        # Rename deepest children first.
        # If we rename the root first, all child full paths change,

        dup_joints.sort(
            key=lambda x: x.count("|"),
            reverse=True
        )

        renamed_root = None

        for jnt in dup_joints:
            short = self.short_name(jnt)
            short = self.clean_duplicate_name(short)

            # Keep the original name and only add _IK or _FK.
            new_name = short + suffix

            renamed_jnt = cmds.rename(jnt, new_name)

            if jnt == dup_root:
                renamed_root = renamed_jnt

        if not renamed_root:
            cmds.warning("Could not find duplicated root.")
            return []

        renamed_root = (cmds.ls(
            renamed_root,
            long=True,
            type="joint"
        ) or [renamed_root])[0]

        # Return the renamed hierarchy from root to children.
        renamed = cmds.listRelatives(
            renamed_root,
            allDescendents=True,
            type="joint",
            fullPath=True
        ) or []

        renamed.reverse()
        renamed = [renamed_root] + renamed

        return renamed

    def duplicate_limb_chain(self, source_chain, suffix):
        new_chain = []

        for source_jnt in source_chain:
            short = self.short_name(source_jnt)
            new_name = short + suffix

            new_jnt = cmds.duplicate(
                source_jnt,
                parentOnly=True,
                name=new_name
            )[0]


            parent = cmds.listRelatives(
                new_jnt,
                parent=True,
                fullPath=True
            ) or []

            if parent:
                new_jnt = cmds.parent(
                    new_jnt,
                    world=True
                )[0]

            new_chain.append(new_jnt)


        for i in range(1, len(new_chain)):
            new_chain[i] = cmds.parent(
                new_chain[i],
                new_chain[i - 1]
            )[0]

        return new_chain

    def duplicate_custom_range(self, chain, suffix):
        """
        Duplicate only the selected custom range.
        Example:
            l_humerus -> l_radius -> l_wrist
        """
        new_chain = []

        for source_jnt in chain:
            short = self.short_name(source_jnt)

            short = self.clean_duplicate_name(short)

            # Keep the original name and only add _IK or _FK at the end.
            new_name = short + suffix

            new_jnt = cmds.duplicate(
                source_jnt,
                parentOnly=True,
                name=new_name
            )[0]

            parent = cmds.listRelatives(new_jnt, parent=True) or []
            if parent:
                new_jnt = cmds.parent(new_jnt, world=True)[0]

            new_chain.append(new_jnt)

        for i in range(1, len(new_chain)):
            new_chain[i] = cmds.parent(new_chain[i], new_chain[i - 1])[0]

        return new_chain

    def rename_joint(self, jnt, suffix):
        short = self.short_name(jnt)
        short = self.clean_duplicate_name(short)
        return short + suffix

    def match_group_to_object(self, group, target):
        temp = cmds.parentConstraint(
            target,
            group,
            maintainOffset=False
        )[0]
        cmds.delete(temp)

    def secondary_axis_vector(self, secondary_axis):
        axis_map = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1)
        }

        return axis_map.get(
            secondary_axis,
            (0, 1, 0)
        )

    def primary_axis_vector(self, primary_axis):
        axis_map = {
            "X": (1, 0, 0),
            "Y": (0, 1, 0),
            "Z": (0, 0, 1)
        }

        return axis_map.get(
            primary_axis,
            (1, 0, 0)
        )

    def primary_rotate_attribute(self, primary_axis):
        attr_map = {
            "X": "rotateX",
            "Y": "rotateY",
            "Z": "rotateZ"
        }

        return attr_map.get(
            primary_axis,
            "rotateX"
        )

    def primary_translate_attribute(self, primary_axis):
        attr_map = {
            "X": "translateX",
            "Y": "translateY",
            "Z": "translateZ"
        }

        return attr_map.get(
            primary_axis,
            "translateX"
        )

    def primary_scale_attribute(self, primary_axis):
        attr_map = {
            "X": "scaleX",
            "Y": "scaleY",
            "Z": "scaleZ"
        }

        return attr_map.get(
            primary_axis,
            "scaleX"
        )
