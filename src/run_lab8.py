import json
from pathlib import Path

from database import check_connection
from pipeline import ParcelPipeline

OUTPUT = Path(__file__).resolve().parents[1] / "output" / "residential_parcels.geojson"


def main():
    if not check_connection():
        print("Cannot continue. Database connection failed.")
        return

    pipeline = ParcelPipeline("Residential")

    first = pipeline.run()
    second = pipeline.run()

    print("[3] Feature count:", len(first["features"]))
    print("[4] Same result:", first == second)

    if first["features"]:
        print("[5] First parcel:", first["features"][0]["id"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(first, indent=2), encoding="utf-8")

    print("[6] Output saved:", OUTPUT.exists(), OUTPUT)


if __name__ == "__main__":
    main()