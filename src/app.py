import json

import psycopg
from flask import Flask, Response, request

from pipeline import ParcelPipeline
from ogc_services import handle_wms, handle_wfs

app = Flask(__name__)

ALLOWED_USES = {"Residential", "Commercial", "Institutional"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "GmE 205 Lab 8"}


@app.get("/api/parcels")
def get_parcels():
    land_use = request.args.get("land_use", "Residential")

    if land_use not in ALLOWED_USES:
        return {"error": "Unsupported land_use value"}, 400

    try:
        collection = ParcelPipeline(land_use).run()
    except psycopg.OperationalError:
        app.logger.exception("PostGIS connection unavailable")
        return {"error": "Spatial database unavailable"}, 503
    except (psycopg.Error, ValueError):
        app.logger.exception("Parcel service failed")
        return {"error": "Could not prepare parcel data"}, 500

    return Response(
        json.dumps(collection),
        mimetype="application/geo+json",
    )


@app.get("/wms")
def wms():
    data = ParcelPipeline("Residential").run()
    body, mime, status = handle_wms(request.args, request.base_url, data)
    return Response(body, status=status, content_type=mime)


@app.get("/wfs")
def wfs():
    data = ParcelPipeline("Residential").run()
    body, mime, status = handle_wfs(request.args, request.base_url, data)
    return Response(body, status=status, content_type=mime)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)