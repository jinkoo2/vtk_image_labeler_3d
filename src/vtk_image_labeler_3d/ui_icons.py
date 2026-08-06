"""Material Design icons for Qt actions/buttons (via qtawesome)."""

from __future__ import annotations

from PyQt5.QtGui import QIcon

_ICON_CACHE = {}

# Material Design Icons (MDI) names: https://pictogrammers.com/library/mdi/
ACTION_ICONS = {
    "Import Image": "mdi.file-image-plus",
    "Open Workspace": "mdi.folder-open",
    "Save Workspace": "mdi.content-save",
    "Close Workspace": "mdi.close-box-outline",
    "Print Object Properties": "mdi.printer",
    "Preferences...": "mdi.cog-outline",
    "Check for Updates...": "mdi.update",
    "About...": "mdi.information-outline",
    "Feature Request...": "mdi.lightbulb-on-outline",
    "Bug Report...": "mdi.bug-outline",
    "Zoom In": "mdi.magnify-plus-outline",
    "Zoom Out": "mdi.magnify-minus-outline",
    "Zoom Reset": "mdi.magnify-scan",
    "Zoom": "mdi.magnify",
    "Pan": "mdi.hand-back-left-outline",
    "Rot +90": "mdi.rotate-right",
    "Rot -90": "mdi.rotate-left",
    "Flip X": "mdi.flip-horizontal",
    "Flip Y": "mdi.flip-vertical",
    "Add Ruler": "mdi.ruler",
    "Paint Tool": "mdi.brush",
    "Pencil Tool": "mdi.pencil-outline",
    "Boolean Tool": "mdi.set-merge",
    "nnUNet Prediction Tool": "mdi.brain",
    "Scribble Tool": "mdi.gesture",
    "Interpolation Tool": "mdi.animation-outline",
    "Extract Largest Component": "mdi.select-group",
    "Binary Morphology Tool": "mdi.circle-expand",
    "Segmentations": "mdi.layers-outline",
    "Points": "mdi.circle-medium",
    "Lines": "mdi.vector-line",
    "Rects": "mdi.rectangle-outline",
    "nnUNet Dashboard": "mdi.cloud-outline",
}


def material_icon(name: str, color: str = "#37474F", scale_factor: float = 1.0) -> QIcon:
    """Return a cached QIcon for an MDI name; empty icon if qtawesome is missing."""
    key = (name, color, scale_factor)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    try:
        import qtawesome as qta

        icon = qta.icon(name, color=color, scale_factor=scale_factor)
    except Exception:
        icon = QIcon()
    _ICON_CACHE[key] = icon
    return icon


def icon_for_action(text: str) -> QIcon:
    """Map a menu/toolbar action label to a Material icon."""
    mdi = ACTION_ICONS.get(text)
    if not mdi:
        # soft match without ellipsis / punctuation differences
        for label, name in ACTION_ICONS.items():
            if label.rstrip(".").lower() == text.rstrip(".").lower():
                mdi = name
                break
    if not mdi:
        return QIcon()
    return material_icon(mdi)


def apply_icon(action, text: str = None) -> None:
    """Set a Material icon on a QAction from its text (or override text)."""
    if action is None:
        return
    label = text if text is not None else action.text()
    icon = icon_for_action(label)
    if not icon.isNull():
        action.setIcon(icon)
