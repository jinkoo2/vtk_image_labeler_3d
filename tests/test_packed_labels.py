from packed_labels import expand_packed_segmentations, label_value_of, packed_labels_payload


def test_label_value_of():
    assert label_value_of({"label": 3}) == 3
    assert label_value_of({"label_value": "7"}) == 7
    assert label_value_of({"label": 0}) is None
    assert label_value_of({"name": "HU1"}) is None


def test_expand_packed_segmentations_from_map():
    segs = expand_packed_segmentations(
        {
            "packed_labels": {
                "file": "2.seg/masks_packed.mha",
                "labels": {"2": "HU2", "1": "HU1"},
            }
        }
    )
    assert [row["name"] for row in segs] == ["HU1", "HU2"]
    assert segs[0]["label"] == 1
    assert segs[0]["file"] == "2.seg/masks_packed.mha"


def test_expand_packed_segmentations_fills_existing():
    segs = expand_packed_segmentations(
        {
            "packed_labels": {
                "file": "2.seg/masks_packed.mha",
                "labels": {"1": "HU1"},
            },
            "segmentations": [{"name": "HU1", "color": [255, 0, 0], "alpha": 0.4}],
        }
    )
    assert segs[0]["label"] == 1
    assert segs[0]["file"] == "2.seg/masks_packed.mha"
    assert segs[0]["color"] == [255, 0, 0]


def test_packed_labels_payload():
    payload = packed_labels_payload("2.seg/masks_packed.mha", {"HU1": 1, "HU2": 2})
    assert payload["file"] == "2.seg/masks_packed.mha"
    assert payload["labels"]["1"] == "HU1"
