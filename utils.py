import arrow
import time
import pandas as pd
from data_definitions import (
    GeodesignhubDataShadowGenerationRequest,
    RoadsDownloadRequest,
    RoadsShadowOverlap,
    ShadowsRoadsIntersectionRequest,
    TreesDownloadRequest,
    RoadsShadowsComputationStartRequest,
    BuildingsDownloadRequest,
    ExistingBuildingsDataShadowGenerationRequest,
    ExistingBuildingsFeatureProperties,
    DrawnTreesShadowGenerationRequest,
    ErrorResponse,
    DrawnTreesFeatureProperties,
)
from typing import Union
import geojson
from dacite import from_dict
from pyproj import Geod
import geopandas as gpd
import pybdshadow
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.geometry import shape
from shapely.geometry.polygon import Polygon
from shapely.geometry.polygon import orient
import json
import uuid
from typing import List
import requests
import numpy as np
from dataclasses import asdict
from conn import get_redis
from shapely import STRtree
import os
import hashlib
from geojson import Feature, FeatureCollection, Polygon, LineString, Point
from dotenv import load_dotenv, find_dotenv
import logging
from pyproj.exceptions import GeodError as GeodError

logger = logging.getLogger("local-climate-response")

load_dotenv(find_dotenv())
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
r = get_redis()


def get_default_shadow_datetime():
    current_year = arrow.now().year
    august_6_date = "{year}-08-06T10:10:00".format(year=current_year)
    return august_6_date


class DrawnTreesProcessor:
    def process_drawn_trees_data(
        self, unprocessed_tree_geojson
    ) -> Union[ErrorResponse, FeatureCollection]:
        """This method buffers the drawn trees GeoJSON as polygon and height"""

        my_geometry_helper = GeometryHelper()
        _all_features: List[Feature] = []
        buffered_tree_features = my_geometry_helper.buffer_tree_points(
            drawn_tree_geojson_features=unprocessed_tree_geojson
        )
        for _buffered_tree_feature in buffered_tree_features["features"]:
            _geometry = Polygon(
                coordinates=_buffered_tree_feature["geometry"]["coordinates"]
            )
            # We must use Building_id in the properties
            _feature_property = DrawnTreesFeatureProperties(
                height=10, base_height=0, color="#FF0000", building_id=str(uuid.uuid4())
            )
            _feature = Feature(geometry=_geometry, properties=asdict(_feature_property))
            _all_features.append(_feature)

        _drawn_trees_feature_collection = FeatureCollection(features=_all_features)

        return _drawn_trees_feature_collection


def download_roads(roads_download_request: RoadsDownloadRequest):
    _roads_download_request = from_dict(
        data_class=RoadsDownloadRequest, data=roads_download_request
    )
    bounds = _roads_download_request.bounds
    roads_url = _roads_download_request.roads_url
    session_roads_key = (
        _roads_download_request.session_id
        + ":"
        + _roads_download_request.request_date_time
        + ":"
        + "roads"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()

    """A function to download roads GeoJSON from GDH data server for the given bounds,  """
    fc = {"type": "FeatureCollection", "features": []}
    roads_storage_key = bounds_hash[:15] + ":roads"
    r.set(session_roads_key, roads_storage_key)
    r.expire(session_roads_key, time=6000)

    if r.exists(roads_storage_key):
        fc_str = r.get(roads_storage_key)
        fc = json.loads(fc_str)

    else:
        bounds_filtering = os.getenv("USE_BOUNDS_FILTERING", None)
        if bounds_filtering:
            # If bounds filtering is enabled, the bounds parameter in the URL is replaced with the current bounds
            r_url = roads_url.replace("__bounds__", bounds)
        else:
            r_url = roads_url
        download_request = requests.get(r_url)
        if download_request.status_code == 200:
            fc = download_request.json()
            r.set(roads_storage_key, json.dumps(fc))
        else:
            logger.error("Error in setting downloaded roads to local memory")
            r.set(
                roads_storage_key,
                json.dumps({"type": "FeatureCollection", "features": []}),
            )

        r.expire(roads_storage_key, time=60000)

    return fc


def download_trees(trees_download_request: TreesDownloadRequest):
    _trees_download_request = from_dict(
        data_class=TreesDownloadRequest, data=trees_download_request
    )
    bounds = _trees_download_request.bounds
    trees_url = _trees_download_request.trees_url
    session_trees_key = (
        _trees_download_request.session_id
        + ":"
        + _trees_download_request.request_date_time
        + ":"
        + "trees"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()

    """A function to download roads GeoJSON from GDH data server for the given bounds,  """
    fc = {"type": "FeatureCollection", "features": []}
    trees_storage_key = bounds_hash[:15] + ":trees"

    r.set(session_trees_key, trees_storage_key)
    r.expire(session_trees_key, time=6000)

    if r.exists(trees_storage_key):
        fc_str = r.get(trees_storage_key)
        fc = json.loads(fc_str)
    else:
        bounds_filtering = os.getenv("USE_BOUNDS_FILTERING", None)
        if bounds_filtering:
            # If bounds filtering is enabled, the bounds parameter in the URL is replaced with the current bounds
            t_url = trees_url.replace("__bounds__", bounds)
        else:
            t_url = trees_url

        download_request = requests.get(t_url)
        if download_request.status_code == 200:
            fc = download_request.json()
            r.set(trees_storage_key, json.dumps(fc))
        else:
            logger.error("Error")
            r.set(
                trees_storage_key,
                json.dumps({"type": "FeatureCollection", "features": []}),
            )
        r.expire(trees_storage_key, time=60000)

    return fc


def download_existing_buildings(buildings_download_request: BuildingsDownloadRequest):
    _buildings_download_request = from_dict(
        data_class=BuildingsDownloadRequest, data=buildings_download_request
    )
    bounds = _buildings_download_request.bounds
    _buildings_url = _buildings_download_request.buildings_url
    session_existing_buildings_key = (
        _buildings_download_request.session_id
        + ":"
        + _buildings_download_request.request_date_time
        + ":"
        + "existing_buildings"
    )
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()

    """A function to download roads GeoJSON from GDH data server for the given bounds,  """
    fc = {"type": "FeatureCollection", "features": []}
    buildings_storage_key = bounds_hash[:15] + ":existing_buildings"

    r.set(session_existing_buildings_key, buildings_storage_key)
    r.expire(session_existing_buildings_key, time=6000)

    if r.exists(buildings_storage_key):
        fc_str = r.get(buildings_storage_key)
        fc = json.loads(fc_str)
    else:
        bounds_filtering = os.getenv("USE_BOUNDS_FILTERING", None)
        if bounds_filtering:
            # If bounds filtering is enabled, the bounds parameter in the URL is replaced with the current bounds
            b_url = _buildings_url.replace("__bounds__", bounds)
        else:
            b_url = _buildings_url

        download_request = requests.get(b_url)
        if download_request.status_code == 200:
            fc = {"type": "FeatureCollection", "features": []}
            raw_fc = download_request.json()
            # Check the FC
            for f in raw_fc["features"]:
                _f_prop = f["properties"]
                new_prop = ExistingBuildingsFeatureProperties(
                    height=_f_prop["max_height"],
                    base_height=0,
                    building_id=str(uuid.uuid4()),
                )
                f["properties"] = asdict(new_prop)
                fc["features"].append(f)

            r.set(buildings_storage_key, json.dumps(fc))
        else:
            logger.error("Error")
            r.set(
                buildings_storage_key,
                json.dumps({"type": "FeatureCollection", "features": []}),
            )
        r.expire(buildings_storage_key, time=60000)

    return fc


class GeometryHelper:
    def buffer_tree_points(self, drawn_tree_geojson_features):
        df = gpd.GeoDataFrame.from_features(drawn_tree_geojson_features)
        df["geometry"] = df["geometry"].buffer(0.00005)
        point_json = df.to_json()
        buffered_point_gj = json.loads(point_json)

        return buffered_point_gj

    def create_point_grid(self, geojson_feature):
        """This function takes a policy polygon feature and generates a point grid"""

        x_spacing = 0.001  # The point spacing you want
        y_spacing = 0.001
        df = gpd.GeoDataFrame.from_features([geojson_feature])

        (
            xmin,
            ymin,
            xmax,
            ymax,
        ) = df.total_bounds  # Find the bounds of all polygons in the df
        xcoords = [c for c in np.arange(xmin, xmax, x_spacing)]  # Create x coordinates
        ycoords = [c for c in np.arange(ymin, ymax, y_spacing)]  # And y

        coordinate_pairs = np.array(np.meshgrid(xcoords, ycoords)).T.reshape(
            -1, 2
        )  # Create all combinations of xy coordinates
        geometries = gpd.points_from_xy(
            coordinate_pairs[:, 0], coordinate_pairs[:, 1]
        )  # Create a list of shapely points

        point_df = gpd.GeoDataFrame(
            geometry=geometries, crs=df.crs
        )  # Create the point df
        point_df["geometry"] = point_df["geometry"].buffer(0.00005)
        point_json = point_df.to_json()
        point_gj = json.loads(point_json)
        # TODO Filter the points to keep within bounds of the polygon
        # filtered_points = df.within(df.at[0,'geometry'])
        # logger.info(filtered_points)
        return point_gj


def kickoff_gdh_roads_shadows_stats(roads_shadow_computation_start):
    _roads_shadow_computation_details = from_dict(
        data_class=RoadsShadowsComputationStartRequest,
        data=roads_shadow_computation_start,
    )

    shadows_key = (
        _roads_shadow_computation_details.session_id
        + ":"
        + _roads_shadow_computation_details.request_date_time
        + "_gdh_buildings_canopy_shadow"
    )
    shadows_str = r.get(shadows_key)
    shadows = json.loads(shadows_str.decode("utf-8"))
    bounds = _roads_shadow_computation_details.bounds
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    roads_storage_key = bounds_hash[:15] + ":roads"
    roads_str = r.get(roads_storage_key)
    roads = json.loads(roads_str.decode("utf-8"))

    shadow_roads_intersection_data = ShadowsRoadsIntersectionRequest(
        roads=json.dumps(roads),
        shadows=shadows,
        job_id=_roads_shadow_computation_details.session_id + ":gdh_roads_shadow",
    )

    compute_road_shadow_overlap(
        roads_shadows_data=asdict(shadow_roads_intersection_data)
    )
    # logger.info(shadow_roads_intersection_data)


def drawn_trees_compute_shadow(tree_processing_payload: dict):
    """This method computes the shadow of drawn trees"""

    _drawn_trees_shadow_request = from_dict(
        data_class=DrawnTreesShadowGenerationRequest,
        data=tree_processing_payload,
    )

    # buffer them
    my_drawn_trees_helper = DrawnTreesProcessor()
    _processed_trees = my_drawn_trees_helper.process_drawn_trees_data(
        unprocessed_tree_geojson=_drawn_trees_shadow_request.trees
    )

    _drawn_trees_shadow_request.processed_trees = _processed_trees
    _date_time = arrow.get(_drawn_trees_shadow_request.request_date_time).isoformat()

    processed_trees_serialzed = json.loads(geojson.dumps(_processed_trees))
    trees = gpd.GeoDataFrame.from_features(processed_trees_serialzed["features"])
    _shadow_date_time = get_default_shadow_datetime()
    _pd_date_time = pd.to_datetime(_shadow_date_time).tz_localize("UTC")
    shadows = pybdshadow.bdshadow_sunlight(trees, _pd_date_time)
    dissolved_shadows = shadows.dissolve()

    redis_key = (
        _drawn_trees_shadow_request.session_id
        + "_"
        + _drawn_trees_shadow_request.state_id
        + "_drawn_trees_shadow"
    )
    
    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Job Completed...")


def compute_existing_buildings_shadow_with_tree_canopy(geojson_session_date_time: dict):
    _existing_building_date_time = from_dict(
        data_class=ExistingBuildingsDataShadowGenerationRequest,
        data=geojson_session_date_time,
    )
    _date_time = arrow.get(_existing_building_date_time.request_date_time).isoformat()
    _pd_date_time = pd.to_datetime(_date_time).tz_convert("UTC")
    # Combine trees and buildings into one FC

    bounds = _existing_building_date_time.bounds
    bounds_hash = hashlib.sha512(bounds.encode("utf-8")).hexdigest()
    trees_hash_key = bounds_hash[:15] + ":trees"
    existing_buildings_hash_key = bounds_hash[:15] + ":existing_buildings"

    _existing_buildings_raw = r.get(existing_buildings_hash_key)
    existing_buildings_fc = json.loads(_existing_buildings_raw)

    existing_buildings = gpd.GeoDataFrame.from_features(
        existing_buildings_fc["features"]
    )

    existing_buildings_shadows = pybdshadow.bdshadow_sunlight(
        existing_buildings, _pd_date_time
    )

    # Merge the canopy with the shadow
    downloaded_trees_raw = r.get(trees_hash_key)
    downloaded_tree_canopy_fc = json.loads(downloaded_trees_raw)
    _downloaded_tree_canopy_features = downloaded_tree_canopy_fc["features"]
    canopy_gdf = gpd.GeoDataFrame.from_features(_downloaded_tree_canopy_features)

    ## Merge the downloaded tree canopy with shadows
    combined_shadows = pd.concat([existing_buildings_shadows, canopy_gdf])

    dissolved_shadows = combined_shadows.dissolve()

    redis_key = (
        _existing_building_date_time.session_id
        + ":"
        + _existing_building_date_time.request_date_time
        + "_existing_buildings_canopy_shadow"
    )
    r.set(redis_key, dissolved_shadows.to_json())
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Existing Buildings + Canopy Shadow Completed")


def compute_gdh_shadow_with_tree_canopy(geojson_session_date_time: dict):
    _diagramid_building_date_time = from_dict(
        data_class=GeodesignhubDataShadowGenerationRequest,
        data=geojson_session_date_time,
    )
    _date_time = arrow.get(_diagramid_building_date_time.request_date_time).isoformat()
    gdh_design_diagram_buildings = gpd.GeoDataFrame.from_features(
        _diagramid_building_date_time.buildings["features"]
    )
    exploded_gdh_buildings = gdh_design_diagram_buildings.explode()
    _exploded_gdh_building_polygons = exploded_gdh_buildings[
        exploded_gdh_buildings.geometry.type != "LineString"
    ]

    _pd_date_time = pd.to_datetime(_date_time).tz_convert("UTC")
    shadows = pybdshadow.bdshadow_sunlight(
        _exploded_gdh_building_polygons, _pd_date_time
    )

    # # Merge the canopy with the shadow
    # bounds = _diagramid_building_date_time.bounds
    # # Combine trees and buildings into one FC
    # bounds_hash= hashlib.sha512(bounds.encode('utf-8')).hexdigest()
    # bounds_hash_key = bounds_hash[:15] + ':trees'
    # downloaded_trees_raw = r.get(bounds_hash_key)

    # downloaded_tree_canopy_fc = json.loads(downloaded_trees_raw)
    # _downloaded_tree_canopy_features = downloaded_tree_canopy_fc['features']
    # canopy_gdf = gpd.GeoDataFrame.from_features(_downloaded_tree_canopy_features)

    # ## Merge the downloaded tree canopy with shadows
    # combined_shadows = pd.concat([shadows, canopy_gdf])

    dissolved_shadows = shadows.dissolve()

    redis_key = (
        _diagramid_building_date_time.session_id
        + ":"
        + _diagramid_building_date_time.request_date_time
        + "_gdh_buildings_canopy_shadow"
    )
    r.set(redis_key, json.dumps(dissolved_shadows.to_json()))
    r.expire(redis_key, time=6000)
    time.sleep(7)
    logger.info("Job Completed")


def compute_polygon_area(polygon: Polygon):
    geod = Geod(ellps="WGS84")
    poly_area_m2, poly_perimeter = geod.geometry_area_perimeter(polygon)
    poly_area_hectares = poly_area_m2 / 10000  # convert from m^2 to hectares
    return poly_area_hectares


def compute_road_shadow_overlap(
    roads_shadows_data: ShadowsRoadsIntersectionRequest,
) -> RoadsShadowOverlap:
    _roads_shadows_data = from_dict(
        data_class=ShadowsRoadsIntersectionRequest, data=roads_shadows_data
    )
    roads_str = _roads_shadows_data.roads
    shadows_str = _roads_shadows_data.shadows

    job_id = _roads_shadows_data.job_id
    geod = Geod(ellps="WGS84")
    roads = json.loads(roads_str)
    shadows = json.loads(shadows_str)

    intersections: List[LineString] = []
    all_roads: List[Union[LineString, MultiLineString]] = []
    all_shadows: List[Polygon] = []

    total_length = 0
    shadowed_kms = 0

    for line_feature in roads["features"]:
        if line_feature["geometry"]["type"] == "LineString":
            line = LineString(coordinates=line_feature["geometry"]["coordinates"])
        elif line_feature["geometry"]["type"] == "MultiLineString":
            line = MultiLineString(line_feature["geometry"]["coordinates"])
        all_roads.append(line)
        segment_length = geod.geometry_length(line)
        logger.info(
            "Segment Length {segment_length:.3f}".format(segment_length=segment_length)
        )
        total_length += segment_length
    total_shadow_area = 0
    for shadow_feature in shadows["features"]:
        s: Polygon = shape(shadow_feature["geometry"])

        poly_area = 0
        if s.geom_type == "MultiPolygon":
            # do multipolygon things.
            all_polygons = list(s.geoms)
            for p in all_polygons:
                oriented = orient(p)
                a = compute_polygon_area(oriented)
                poly_area += a
        elif s.geom_type == "Polygon":
            poly_area = compute_polygon_area(s)
        else:
            raise IOError("Shape is not a polygon.")
        logger.info("Shadow Area {poly_area:.3f}".format(poly_area=poly_area))
        total_shadow_area += poly_area

        all_shadows.append(s)

    roads_tree = STRtree(all_roads)

    for current_s in all_shadows:
        relevant_roads = [
            all_roads[idx]
            for idx in roads_tree.query(current_s, predicate="intersects")
        ]

        for relevant_road in relevant_roads:
            # line_buffered = relevant_road.buffer(0.0001)
            intersection = relevant_road.intersection(current_s)
            intersection_length = geod.geometry_length(intersection)

            logger.info(
                "Intersection Length {intersection_length:.3f}".format(
                    intersection_length=intersection_length
                )
            )

            intersections.append(intersection)
            shadowed_kms += intersection_length
    total_shadow_area_rounded = round(total_shadow_area, 2)
    road_shadow_overlap = RoadsShadowOverlap(
        total_roads_kms=round(total_length, 2),
        shadowed_kms=round(shadowed_kms, 2),
        job_id=job_id,
        total_shadow_area=total_shadow_area_rounded,
    )

    r.set(job_id, json.dumps(asdict(road_shadow_overlap)))
    time.sleep(1)
    logger.info("Intersection Completed")
