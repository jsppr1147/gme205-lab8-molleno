"""GmE 205 Laboratory 8 — GIVEN teaching OGC protocol helpers.

This deliberately small HTTP/KVP implementation offers a discoverable WMS
1.1.1 map layer and a limited WFS 1.0.0 GML2 vector layer to a GIS client.
It is NOT an OGC-certified service, does not claim full conformance, and is
for LOCAL CLASSROOM USE ONLY. No write transactions, complex WFS filters,
authentication, or production security controls.

Students do not modify this module. They add two Flask routes which pass
request.args, request.base_url, and the ParcelPipeline FeatureCollection.
"""
from __future__ import annotations

import json
from html import escape
from math import isfinite
from xml.etree import ElementTree as ET

from map_renderer import render_png

WFS_NS = "http://www.opengis.net/wfs"
GML_NS = "http://www.opengis.net/gml"
APP_NS = "https://gme205.example.org/lab8"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XSD_NS = "http://www.w3.org/2001/XMLSchema"

ET.register_namespace("wfs", WFS_NS)
ET.register_namespace("gml", GML_NS)
ET.register_namespace("lab8", APP_NS)
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("xsd", XSD_NS)


def _param(params, name, default=""):
    return next((v for k, v in params.items() if k.upper() == name.upper()), default)


def _extent(collection):
    coords = []
    def walk(v):
        if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(i, (int, float)) for i in v[:2]):
            coords.append((float(v[0]), float(v[1])))
        elif isinstance(v, (list, tuple)):
            for sub in v:
                walk(sub)
    for feature in collection.get("features", []):
        if feature.get("geometry"):
            walk(feature["geometry"].get("coordinates", []))
    if not coords:
        return (118.0, 0.0, 119.0, 1.0)
    xs, ys = zip(*coords)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    # Guarantee nonzero extents even with a degenerate geometry.
    if minx == maxx:
        minx -= .0001; maxx += .0001
    if miny == maxy:
        miny -= .0001; maxy += .0001
    return (minx, miny, maxx, maxy)


def _bbox_attrs(bounds):
    a, b, c, d = bounds
    return f'minx="{a:.10f}" miny="{b:.10f}" maxx="{c:.10f}" maxy="{d:.10f}"'


def _xml_error(message, service="WMS", status=400):
    msg = escape(str(message))
    if service == "WFS":
        xml = f'<?xml version="1.0" encoding="utf-8"?><ServiceExceptionReport version="1.0.0"><ServiceException>{msg}</ServiceException></ServiceExceptionReport>'
    else:
        xml = f'<?xml version="1.0" encoding="utf-8"?><ServiceExceptionReport version="1.1.1"><ServiceException>{msg}</ServiceException></ServiceExceptionReport>'
    return xml.encode(), "application/vnd.ogc.se_xml", status


def _wms_capabilities(base_url, collection):
    base = escape(base_url + "?", quote=True)
    b = _bbox_attrs(_extent(collection))
    return (f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE WMT_MS_Capabilities SYSTEM "http://schemas.opengis.net/wms/1.1.1/WMS_MS_Capabilities.dtd">
<WMT_MS_Capabilities version="1.1.1" updateSequence="0"
  xmlns:xlink="http://www.w3.org/1999/xlink">
<Service><Name>OGC:WMS</Name><Title>GmE 205 Teaching Parcels WMS</Title>
<Abstract>Local classroom demonstration with simplified operation support.</Abstract>
<OnlineResource xlink:type="simple" xlink:href="{base}"/>
<Fees>none</Fees><AccessConstraints>Local classroom use</AccessConstraints></Service>
<Capability><Request>
<GetCapabilities><Format>application/vnd.ogc.wms_xml</Format><DCPType><HTTP><Get><OnlineResource xlink:type="simple" xlink:href="{base}"/></Get></HTTP></DCPType></GetCapabilities>
<GetMap><Format>image/png</Format><DCPType><HTTP><Get><OnlineResource xlink:type="simple" xlink:href="{base}"/></Get></HTTP></DCPType></GetMap>
</Request><Exception><Format>application/vnd.ogc.se_xml</Format></Exception>
<Layer><Title>GmE 205 Layers</Title><SRS>EPSG:4326</SRS>
<LatLonBoundingBox {b}/><BoundingBox SRS="EPSG:4326" {b}/>
<Layer queryable="0" opaque="0" noSubsets="0"><Name>parcels</Name><Title>Residential Parcels</Title><SRS>EPSG:4326</SRS>
<LatLonBoundingBox {b}/><BoundingBox SRS="EPSG:4326" {b}/>
<Style><Name>default</Name><Title>Default green</Title></Style>
</Layer></Layer></Capability></WMT_MS_Capabilities>''').encode("utf-8")


def handle_wms(params, base_url, collection):
    """Return (body_bytes, content_type, http_status) for /wms GET."""
    operation = _param(params, "REQUEST", "GetCapabilities").lower()
    if _param(params, "SERVICE", "WMS").upper() != "WMS":
        return _xml_error("SERVICE must be WMS")
    if operation == "getcapabilities":
        return _wms_capabilities(base_url, collection), "application/vnd.ogc.wms_xml", 200
    if operation != "getmap":
        return _xml_error("Only GetCapabilities and GetMap are supported")
    try:
        if _param(params, "VERSION", "1.1.1") != "1.1.1":
            raise ValueError("This classroom WMS supports VERSION=1.1.1 only")
        if _param(params, "LAYERS", "") != "parcels":
            raise ValueError("LAYERS must be parcels")
        if _param(params, "SRS", "") != "EPSG:4326":
            raise ValueError("SRS must be EPSG:4326")
        if _param(params, "FORMAT", "image/png").lower() != "image/png":
            raise ValueError("FORMAT must be image/png")
        if _param(params, "STYLES", "") not in ("", "default"):
            raise ValueError("STYLES must be empty or default")
        bbox = [float(v) for v in _param(params, "BBOX", "").split(",")]
        if len(bbox) != 4 or not all(isfinite(v) for v in bbox):
            raise ValueError("BBOX must contain four finite numbers")
        png = render_png(collection, bbox, int(_param(params, "WIDTH", "600")), int(_param(params, "HEIGHT", "600")),
                         _param(params, "TRANSPARENT", "FALSE").upper() == "TRUE")
        return png, "image/png", 200
    except (TypeError, ValueError) as e:
        return _xml_error(str(e))


def _wfs_capabilities(base_url, collection):
    url = escape(base_url, quote=True)
    b = _bbox_attrs(_extent(collection))
    reqs = ""
    for operation in ("GetCapabilities", "DescribeFeatureType", "GetFeature"):
        result = '<ResultFormat><GML2/><GeoJSON/></ResultFormat>' if operation == "GetFeature" else (
            '<SchemaDescriptionLanguage><XMLSCHEMA/></SchemaDescriptionLanguage>' if operation == "DescribeFeatureType" else "")
        reqs += f'<{operation}>{result}<DCPType><HTTP><Get onlineResource="{url}?"/></HTTP></DCPType></{operation}>'
    return (f'''<?xml version="1.0" encoding="UTF-8"?>
<WFS_Capabilities xmlns="{WFS_NS}" xmlns:ogc="http://www.opengis.net/ogc"
 xmlns:gml="{GML_NS}" xmlns:lab8="{APP_NS}" version="1.0.0" updateSequence="0">
<Service><Name>WFS</Name><Title>GmE 205 Teaching Parcels WFS</Title>
<Abstract>Limited WFS 1.0.0 classroom demo.</Abstract><OnlineResource>{url}</OnlineResource>
<Fees>none</Fees><AccessConstraints>Local classroom use</AccessConstraints></Service>
<Capability><Request>{reqs}</Request></Capability>
<FeatureTypeList><Operations><Query/></Operations><FeatureType>
<Name>lab8:parcels</Name><Title>Residential Parcels</Title>
<Abstract>Feature collection from the Lab 8 pipeline.</Abstract><SRS>EPSG:4326</SRS>
<LatLongBoundingBox {b}/></FeatureType></FeatureTypeList>
<ogc:Filter_Capabilities><ogc:Spatial_Capabilities><ogc:Spatial_Operators><ogc:BBOX/></ogc:Spatial_Operators></ogc:Spatial_Capabilities></ogc:Filter_Capabilities>
</WFS_Capabilities>''').encode("utf-8")


def _wfs_xsd():
    # This is a small GML2 application schema for the three properties of parcels.
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="{XSD_NS}" xmlns:gml="{GML_NS}"
 xmlns:lab8="{APP_NS}" targetNamespace="{APP_NS}" elementFormDefault="qualified">
<xsd:import namespace="{GML_NS}" schemaLocation="http://schemas.opengis.net/gml/2.1.2/feature.xsd"/>
<xsd:element name="parcels" type="lab8:ParcelType" substitutionGroup="gml:_Feature"/>
<xsd:complexType name="ParcelType"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType">
<xsd:sequence><xsd:element name="parcel_id" type="xsd:string"/>
<xsd:element name="land_use" type="xsd:string"/>
<xsd:element name="geometry" type="gml:GeometryPropertyType"/>
</xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType></xsd:schema>'''.encode("utf-8")


def _gml_geometry(parent, geom):
    """Append simple GML2 Polygon or MultiPolygon from EPSG:4326 GeoJSON."""
    gtype = geom.get("type")
    data = geom.get("coordinates", [])
    if gtype == "Polygon":
        geometries = [data]
        node = ET.SubElement(parent, f"{{{GML_NS}}}Polygon", srsName="EPSG:4326")
        _gml_polygon_rings(node, data)
    elif gtype == "MultiPolygon":
        multi = ET.SubElement(parent, f"{{{GML_NS}}}MultiPolygon", srsName="EPSG:4326")
        for rings in data:
            member = ET.SubElement(multi, f"{{{GML_NS}}}polygonMember")
            poly = ET.SubElement(member, f"{{{GML_NS}}}Polygon", srsName="EPSG:4326")
            _gml_polygon_rings(poly, rings)
    else:
        raise ValueError(f"This lab supports polygon geometries only, got {gtype}")


def _gml_polygon_rings(poly, rings):
    for i, ring in enumerate(rings):
        edge = ET.SubElement(poly, f"{{{GML_NS}}}{'outerBoundaryIs' if i == 0 else 'innerBoundaryIs'}")
        line = ET.SubElement(edge, f"{{{GML_NS}}}LinearRing")
        text = ET.SubElement(line, f"{{{GML_NS}}}coordinates", decimal=".", cs=",", ts=" ")
        text.text = " ".join(f"{x:.8f},{y:.8f}" for x, y in ring)


def _wfs_gml(collection, base_url, maxfeatures=None):
    root = ET.Element(f"{{{WFS_NS}}}FeatureCollection")
    root.set(f"{{{XSI_NS}}}schemaLocation", f"{APP_NS} {base_url}?SERVICE=WFS&VERSION=1.0.0&REQUEST=DescribeFeatureType&TYPENAME=lab8:parcels")
    for f in collection.get("features", [])[:maxfeatures]:
        member = ET.SubElement(root, f"{{{GML_NS}}}featureMember")
        feature = ET.SubElement(member, f"{{{APP_NS}}}parcels", fid="parcels." + str(f.get("id", "")))
        props = f.get("properties", {})
        for name in ("parcel_id", "land_use"):
            element = ET.SubElement(feature, f"{{{APP_NS}}}{name}")
            element.text = str(props.get(name, f.get("id") if name == "parcel_id" else ""))
        ge = ET.SubElement(feature, f"{{{APP_NS}}}geometry")
        _gml_geometry(ge, f["geometry"])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def handle_wfs(params, base_url, collection):
    """Return (body_bytes, content_type, http_status) for /wfs GET.

    Only GetCapabilities, DescribeFeatureType, and GetFeature are supported.
    No WFS-T, complex filter encoding, sorting or server-side paging.
    """
    if _param(params, "SERVICE", "WFS").upper() != "WFS":
        return _xml_error("SERVICE must be WFS", "WFS")
    operation = _param(params, "REQUEST", "GetCapabilities").lower()
    if operation == "getcapabilities":
        return _wfs_capabilities(base_url, collection), "text/xml", 200
    try:
        if _param(params, "VERSION", "1.0.0") != "1.0.0":
            raise ValueError("This classroom WFS supports VERSION=1.0.0 only")
        if operation == "describefeaturetype":
            return _wfs_xsd(), "text/xml", 200
        if operation != "getfeature":
            raise ValueError("Only GetCapabilities, DescribeFeatureType and GetFeature supported")
        typename = _param(params, "TYPENAME", "lab8:parcels")
        if typename not in ("lab8:parcels", "parcels"):
            raise ValueError("TYPENAME must be lab8:parcels")
        data = dict(collection)
        features = list(collection.get("features", []))
        # Common QGIS bbox filtering is supported. Only lon/lat values are used.
        bbox = _param(params, "BBOX", "")
        if bbox:
            bounds = [float(n) for n in bbox.split(",")[:4]]
            if len(bounds) != 4:
                raise ValueError("Invalid BBOX")
            # Bounds-only check is sufficient for the simple rectangular Lab 6 parcels.
            keep = []
            for f in features:
                b = _extent({"features": [f]})
                if not (b[2] < bounds[0] or b[0] > bounds[2] or b[3] < bounds[1] or b[1] > bounds[3]):
                    keep.append(f)
            features = keep
        count = _param(params, "MAXFEATURES", "")
        if count:
            n = int(count)
            if not 0 <= n <= 10000:
                raise ValueError("MAXFEATURES outside supported range")
            features = features[:n]
        data["features"] = features
        fmt = _param(params, "OUTPUTFORMAT", "GML2").lower()
        if fmt in ("application/json", "application/geo+json", "geojson", "json"):
            return json.dumps(data, separators=(",", ":")).encode("utf-8"), "application/geo+json", 200
        if fmt not in ("gml2", "text/xml", "application/gml+xml", ""):
            raise ValueError("OUTPUTFORMAT supports GML2 or GeoJSON only")
        return _wfs_gml(data, base_url), "text/xml", 200
    except (ValueError, KeyError, TypeError) as e:
        return _xml_error(str(e), "WFS")
