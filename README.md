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

Part D: