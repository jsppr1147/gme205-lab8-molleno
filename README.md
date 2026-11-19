Gme 205 Lab 8: Reproducible Geoprocessing, Flask Services, and QGIS WMS/WFS Clients

## commit logs

Part A: Reusing the Exisiting System
- Created the usual project structure and added the few files `map_render.py` and `ogc_services.py` given by the instructor.  
- Installed usual pip installs and the `flask`.  
- Checked if the database from previous exercise still works. [Still works!].  
- PgAdmin Query shows parcel id: P-001 and P-002 as residential, P-003 as commercial and P-004 as Insitutional.  

Part B: Creating a Reusable OOP Pipeline
- Created pipeline.py by reusing the ff:
    - `database.py` for PostGIS connection and the `fetch_parcels_by_land_use()` query.  
    - `spatial.py` for accessing `Parcel` class that converts a database row into an object.  
    - `exchange.py` for the `build_feature_collection()` and `validate_feature_collection()`.  
- The `ParcelPipeline` class runs the existing steps in a fixed order: fetch rows, build `Parcel` objects, build a GeoJSON FeatureCollection, then validate it.  
- Created a temporary check using the terminal command "python -c "import sys; sys.path.insert(0, 'src'); from pipeline import ParcelPipeline; print(ParcelPipeline('Residential').run()['type'])". returns `FeatureCollection` which means it runs smoothly.  

Part C: Automation, Print, and Comparing Two Runs
- Created `run_lab8.py` for comparing two outputs. The comparison only works if the features come out in the same order. `ORDER BY parcel_id` in the query guarantees that. Without it, PostgreSQL can return rows in any order, so two identical runs could look different even though the data is the same.
- Results:   
    PostGIS: 3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1  
    [3] Feature count: 2  
    [4] Same result: True  
    [5] First parcel: P-001  
    [6] Output saved: True C:\Users\Jasper\Documents\1st Sem 26_27\Programming Class\Lab8\gme205-lab8\output\residential_parcels.geojson  

Part D and E: Exposing the Same Pipeline through Flask and Running Services
- Created `app.py` with four routes: 
    -`/health` for confirming if the Flask is responding and not touching the database
    -`/api/parcels?land_use=...` for returning GeoJSON for the requested land use.
    -`wms` for WMS 1.1.1 GetCapabilities and GetMap (raster map)
    -`wfs` for WFS 1.0.0 GetCapabilities. DescribeFeatureType and GetFeature (vector)
- results:

| Request | Result |
|---|---|
| `/health` | `200, {"status": "ok", ...}` |
| `/api/parcels?land_use=Residential` | `200, 2 features` |
| `/api/parcels?land_use=Commercial` | `200, 1 feature` |
| `/api/parcels?land_use=Unknown` | `400,"error": "Unsupported land_use value"` |
| `/wms?SERVICE=WMS&REQUEST=GetCapabilities` | `XML with layer parcels` |
| `/wfs?SERVICE=WFS&REQUEST=GetCapabilities` | GetCapabilities, DescribeFeatureType, GetFeature	Returned WFS_Capabilities version 1.0.0, titled "GmE 205 Teaching Parcels WFS", advertising GML2 and GeoJSON result formats |

- Screenshots: `evidence/Evidence_Flask_1.jpg`  

Part E: QGIS Connection  
- Created two QGIS connections, a WMS at `http://127.0.0.1:5000/wms` and a WFS at `http://127.0.0.1:5000/wfs`.
- QGIS sends GetCapabilities to discover the layers, then GetMap (WMS) or GetFeature (WFS). Flask runs `ParcelPipeline("Residential")` for each request, and the given helpers build the PNG or GML.  
- results:   
    - WMS: Layer loaded, green parcels with dark blue outlines near latitude 0, longitude ~118.5. Not queryable.  
    - WFS: Layer loaded, rows with parcel_id and land_use columns (P-001 and P-002, Residential). Queryable.  

- Screenshots: `evidence/Evidence_Flask_2.jpg`, `evidence/Evidence_Flask_3.jpg`, `evidence/Evidence_Flask_4.jpg`, `evidence/Evidence_WMS.jpg`, `evidence/Evidence_WFS.jpg`   

Part F: Reflections

1. What was reused from Laboratory 7-8 rather than rewritten?  
`database.py`, `spatial.py` and `exchange.py` were copied from Lab 7 unchanged. `map_renderer.py` and `ogc_services.py` are instructor-provided. Only `pipeline.py`, `run_lab8.py` and `app.py` are new.  

2. Why is ParcelPipeline a useful coordinating object? What should it NOT do?  
It runs fetch, object construction, GeoJSON building and validation in one fixed order, so the script and every Flask route reuse the same logic. It should not hold credentials, define routes, write files, or contain SQL or GeoJSON formatting. Those belong in `.env`/`database.py`, `app.py`, `run_lab8.py` and `exchange.py`.

3. Why must we specify stable query ordering when comparing outputs?  
`first == second` only works if features arrive in the same order. `ORDER BY parcel_id` guarantees that. Without it, PostgreSQL may return rows in any order, so identical data could still compare as different.  
 
4. What is the difference between a saved .geojson file and the Flask endpoint?   
The file is a snapshot written once by `run_lab8.py`. The endpoint runs the pipeline on every request, so it returns current database contents and accepts a `land_use` parameter. Both use the same pipeline and structure.  

5. How do the temporary prints and HTTP responses help locate a failed boundary?   
Each print or status code checks one stage. For example, a failed connection print points to the database, a wrong count points to the query or data, `Same result: False` points to ordering, and a 400 or 503 from Flask points to input validation or database availability. The first wrong output shows where to look.   

6. WMS vs WFS in QGIS: what can you inspect in the vector attribute table that you cannot inspect in the rendered WMS image?  
The WMS returns a rendered PNG, so QGIS only displays pixels and cannot read any parcel data. The WFS returns vector features, so the attribute table shows `parcel_id` and `land_use` for each parcel, and the features can be selected, identified and queried. The classroom service is not OGC-certified.  