"""GmE 205 Laboratory 8 — GIVEN (do not modify).

Rasterize existing EPSG:4326 GeoJSON features into a georeferenced PNG map
for a small classroom WMS-style service. No HTML / JS / frontend required.

The file purposely does NOT open a database or define Flask routes.
It is only responsible for rendering. The students wire it through the
provided OGC helper and their existing ParcelPipeline.
"""
from __future__ import annotations

from io import BytesIO
from math import isfinite

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Polygon as MplPolygon


def _draw_geometry(ax, geometry):
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "Polygon":
        polygons = [coords]
    elif kind == "MultiPolygon":
        polygons = coords
    else:
        # For this laboratory, only parcel polygons are rendered.
        return

    for polygon_rings in polygons:
        if not polygon_rings:
            continue
        ax.add_patch(MplPolygon(
            polygon_rings[0], closed=True,
            facecolor="#3CBFA9", edgecolor="#123B58", linewidth=1.0,
        ))
        # Show interior rings as background-colored cutouts in this
        # introductory renderer. For production, use a topology-aware
        # rendering engine supporting polygon holes and compositing.
        for hole in polygon_rings[1:]:
            ax.add_patch(MplPolygon(
                hole, closed=True,
                facecolor="white", edgecolor="#123B58", linewidth=0.6,
            ))


def render_png(feature_collection, bbox, width, height, transparent=False):
    """Return PNG bytes of parcel features in an EPSG:4326 bounding box.

    Parameters
    ----------
    feature_collection : dict
        GeoJSON FeatureCollection; must already use lon/lat (EPSG:4326).
    bbox : iterable[float]
        (west, south, east, north), WMS 1.1.1 / EPSG:4326 order.
    width, height : int
        Requested output image dimensions in pixels.
    transparent : bool
        Draw a transparent PNG background when True.
    """
    if feature_collection.get("type") != "FeatureCollection":
        raise ValueError("Expected GeoJSON FeatureCollection")
    west, south, east, north = (float(v) for v in bbox)
    if not all(map(isfinite, [west, south, east, north])):
        raise ValueError("BBOX must contain finite coordinates")
    if not (west < east and south < north):
        raise ValueError("BBOX must be west,south,east,north")
    width, height = int(width), int(height)
    if not (32 <= width <= 2048 and 32 <= height <= 2048):
        raise ValueError("WIDTH and HEIGHT must be between 32 and 2048")

    dpi = 100
    figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor="none" if transparent else "white")
    FigureCanvasAgg(figure)
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_xlim(west, east)
    axis.set_ylim(south, north)
    axis.set_aspect("auto")  # WMS BBOX determines view; WIDTH/HEIGHT determine pixel shape.
    axis.set_axis_off()
    axis.set_facecolor("none" if transparent else "white")

    for feature in feature_collection.get("features", []):
        if isinstance(feature, dict) and isinstance(feature.get("geometry"), dict):
            _draw_geometry(axis, feature["geometry"])

    output = BytesIO()
    figure.savefig(output, format="png", dpi=dpi, transparent=transparent, pad_inches=0)
    figure.clear()
    return output.getvalue()
