from database import fetch_parcels_by_land_use
from spatial import Parcel
from exchange import (
    build_feature_collection,
    validate_feature_collection,
)


class ParcelPipeline:
    def __init__(self, land_use):
        self.land_use = land_use

    def run(self):
        rows = fetch_parcels_by_land_use(self.land_use)
        parcels = [Parcel.from_row(row) for row in rows]
        collection = build_feature_collection(parcels)
        validate_feature_collection(collection)
        return collection