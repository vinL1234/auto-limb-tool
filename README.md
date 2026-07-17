# Auto Limb Tool

A modular Autodesk Maya Python tool for building IK/FK limb rigs, stretch systems,
and roll joints.

## Modules

- `core.py` — joint-chain queries, duplication, naming, and axis helpers
- `rig.py` — IK/FK chains, controls, constraints, switching, and visibility
- `roll.py` — upper/lower limb roll joints and midpoint behavior
- `stretch.py` — standard and custom stretch systems
- `ui.py` — Maya user interface and build coordination
- `app.py` — composes the modules into `AutoLimbBuilder`

## Installation

1. Copy the repository folder to a location included in Maya's Python path, or
   add the repository folder to `sys.path`.
2. In Maya's Python Script Editor, run:

```python
from auto_limb_tool import show
show()
```

For a quick launch, you can also run the top-level `auto_limb_tool.py` file from
Maya's Python Script Editor.

## Requirements

- Autodesk Maya
- Maya's bundled Python environment (`maya.cmds`)
