import csv
import json
import os
import sys

EXCLUDE_PREFIXES = ("PTV", "CTV", "GTV", "ITV")


def extract_structures(input_csv):
    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        seen = set()
        structures = []
        for row in reader:
            name = row["Structure Template"].strip()
            if name in seen:
                continue
            if any(name.upper().startswith(p) for p in EXCLUDE_PREFIXES):
                continue
            seen.add(name)
            structures.append(name)

    # Write structures CSV
    structures_csv = input_csv + ".structures.csv"
    with open(structures_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Structure"])
        for i, name in enumerate(structures, start=1):
            writer.writerow([i, name])
    print(f"Wrote {len(structures)} structures to {structures_csv}")

    # Write dataset JSON
    base_name = os.path.splitext(os.path.basename(input_csv))[0]
    labels = {"background": 0}
    for i, name in enumerate(structures, start=1):
        labels[name] = i

    dataset = {
        "name": base_name,
        "description": f"Structures extracted from {os.path.basename(input_csv)}",
        "reference": "Stony Brook Univ Hospital",
        "licence": "CC-BY-SA 4.0",
        "tensorImageSize": "3D",
        "labels": labels,
        "channel_names": {"0": "CT"},
        "file_ending": ".mha",
        "numTraining": 0,
        "numTest": 0,
        "id": f"Dataset000_{base_name}",
    }

    dataset_json = input_csv + ".dataset.json"
    with open(dataset_json, "w") as f:
        json.dump(dataset, f, indent=4)
    print(f"Wrote dataset JSON to {dataset_json}")


if __name__ == "__main__":
    input_file = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(os.path.dirname(__file__), "TG101.csv")
    )
    extract_structures(input_file)
