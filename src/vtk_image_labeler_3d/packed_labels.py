"""Packed / composite label fields on vtk_image_labeler_3d project JSON."""

from __future__ import annotations


def label_value_of(item: dict | None) -> int | None:
    """Integer label id on a segmentation layer (``label`` or ``label_value``)."""
    if not isinstance(item, dict):
        return None
    raw = item.get("label")
    if raw is None:
        raw = item.get("label_value")
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _packed_name_to_value(packed: dict) -> dict[str, int]:
    labels = packed.get("labels") if isinstance(packed.get("labels"), dict) else {}
    out: dict[str, int] = {}
    for key, name in labels.items():
        try:
            out[str(name)] = int(key)
        except (TypeError, ValueError):
            continue
    return out


def expand_packed_segmentations(data: dict | None) -> list[dict]:
    """Fill ``label`` / ``file`` from ``packed_labels``, or create layers from that map."""
    data = data if isinstance(data, dict) else {}
    packed = data.get("packed_labels") if isinstance(data.get("packed_labels"), dict) else {}
    packed_file = str(packed.get("file") or "").replace("\\", "/")
    name_to_value = _packed_name_to_value(packed)
    existing = [dict(item) for item in (data.get("segmentations") or []) if isinstance(item, dict)]
    if not existing and packed_file and name_to_value:
        items = []
        for name, value in name_to_value.items():
            items.append(
                {
                    "name": name,
                    "file": packed_file,
                    "label": value,
                    "alpha": 0.45,
                }
            )
        items.sort(key=lambda row: int(row["label"]))
        return items
    out: list[dict] = []
    for item in existing:
        name = str(item.get("name") or "")
        if label_value_of(item) is None and name in name_to_value:
            item["label"] = name_to_value[name]
        if not str(item.get("file") or "").strip() and packed_file:
            item["file"] = packed_file
        out.append(item)
    return out


def packed_labels_payload(file_rel: str, name_to_value: dict[str, int]) -> dict:
    labels = {str(value): name for name, value in name_to_value.items() if value}
    return {"file": str(file_rel).replace("\\", "/"), "labels": labels}
