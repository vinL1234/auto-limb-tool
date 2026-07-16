"""Auto Limb Tool for Autodesk Maya."""

from .app import AutoLimbBuilder, VincentLimbBuilder


def show():
    """Open the Auto Limb Tool window."""
    return AutoLimbBuilder().show()


__all__ = ["AutoLimbBuilder", "VincentLimbBuilder", "show"]
