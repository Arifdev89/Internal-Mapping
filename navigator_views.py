
import heapq
import json
import math

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.http import JsonResponse
from django.db import connection, DatabaseError
from django.views.decorators.http import require_GET

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction, DatabaseError
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import (
    Organisation,
    Building,
    Entrance,
    Floor,
    Location,
    NavigationNode,
    NavigationEdge,
    QRLocation,
)


# ============================================================
# HOME PAGE
# ============================================================

@ensure_csrf_cookie
def index(request):
    return render(request, "navigator/index.html")


# ============================================================
# DATABASE STATUS
# ============================================================

@require_GET
def database_status_api(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return JsonResponse({
            "success": True,
            "database": "connected",
            "message": "Database connected successfully.",
        })

    except DatabaseError:
        return JsonResponse({
            "success": False,
            "database": "disconnected",
            "message": "Database connection failed.",
        }, status=503)


# ============================================================
# COMMON HELPERS
# ============================================================

def building_coordinates(building):
    entrance = Entrance.objects.filter(
        building=building,
        is_main=True,
    ).first()

    if entrance:
        return {
            "latitude": float(entrance.latitude),
            "longitude": float(entrance.longitude),
        }

    return {
        "latitude": float(building.latitude),
        "longitude": float(building.longitude),
    }


def node_data(node):
    return {
        "id": node.id,
        "code": node.code,
        "name": node.name,
        "node_type": node.node_type,
        "floor_id": node.floor_id,
        "floor_name": node.floor.name,
        "x": float(node.x),
        "y": float(node.y),
        "location_id": node.location_id,
    }


# ============================================================
# BUILDING LIST API
# ============================================================

@require_GET
def building_list_api(request):
    buildings = (
        Building.objects
        .filter(is_active=True)
        .annotate(floor_count=Count("floors"))
        .order_by("name")
    )

    results = []

    for building in buildings:
        coordinates = building_coordinates(building)

        results.append({
            "id": building.id,
            "name": building.name,
            "building_type": building.building_type,
            "address": building.address,
            "latitude": coordinates["latitude"],
            "longitude": coordinates["longitude"],
            "source": building.source,
            "floor_count": building.floor_count,
        })

    return JsonResponse({
        "success": True,
        "count": len(results),
        "results": results,
    })


# ============================================================
# LOCAL PLACE SEARCH API
# ============================================================

@require_GET
def search_places(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({
            "success": False,
            "error": "Enter at least 2 characters.",
        }, status=400)

    buildings = (
        Building.objects
        .filter(is_active=True)
        .filter(
            Q(name__icontains=query)
            | Q(address__icontains=query)
        )[:10]
    )

    results = []

    for building in buildings:
        coordinates = building_coordinates(building)

        results.append({
            "id": building.id,
            "name": building.name,
            "address": building.address,
            "latitude": coordinates["latitude"],
            "longitude": coordinates["longitude"],
            "building_type": building.building_type,
            "source": building.source,
            "result_type": "building",
        })

    entrances = (
        Entrance.objects
        .filter(building__is_active=True)
        .filter(name__icontains=query)[:10]
    )

    for entrance in entrances:
        results.append({
            "id": entrance.id,
            "name": entrance.name,
            "building_id": entrance.building_id,
            "building_name": entrance.building.name,
            "latitude": float(entrance.latitude),
            "longitude": float(entrance.longitude),
            "result_type": "entrance",
        })

    locations = (
        Location.objects
        .filter(is_active=True)
        .filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
        )[:10]
    )

    for location in locations:
        results.append({
            "id": location.id,
            "name": location.name,
            "category": location.category,
            "floor_id": location.floor_id,
            "floor_name": location.floor.name,
            "building_id": location.floor.building_id,
            "building_name": location.floor.building.name,
            "result_type": "indoor_location",
        })

    return JsonResponse({
        "success": True,
        "query": query,
        "count": len(results),
        "results": results,
    })


# ============================================================
# BUILDING FLOORS API
# ============================================================

@require_GET
def building_floors_api(request, building_id):
    building = get_object_or_404(
        Building,
        id=building_id,
        is_active=True,
    )

    floors = Floor.objects.filter(
        building=building
    ).order_by("level")

    results = []

    for floor in floors:
        results.append({
            "id": floor.id,
            "level": floor.level,
            "name": floor.name,
            "svg_width": floor.svg_width,
            "svg_height": floor.svg_height,
            "meters_per_unit": float(floor.meters_per_unit),
        })

    return JsonResponse({
        "success": True,
        "building_id": building.id,
        "building_name": building.name,
        "count": len(results),
        "results": results,
    })


# ============================================================
# FLOOR LOCATIONS API
# ============================================================

@require_GET
def floor_locations_api(request, floor_id):
    floor = get_object_or_404(Floor, id=floor_id)

    locations = Location.objects.filter(
        floor=floor,
        is_active=True,
    ).order_by("name")

    results = []

    for location in locations:
        results.append({
            "id": location.id,
            "name": location.name,
            "category": location.category,
            "description": location.description,
            "x": float(location.x),
            "y": float(location.y),
            "width": float(location.width),
            "height": float(location.height),
            "is_restricted": location.is_restricted,
        })

    return JsonResponse({
        "success": True,
        "floor_id": floor.id,
        "count": len(results),
        "results": results,
    })


# ============================================================
# FLOOR NAVIGATION NODES API
# ============================================================

@require_GET
def floor_nodes_api(request, floor_id):
    floor = get_object_or_404(Floor, id=floor_id)

    nodes = NavigationNode.objects.filter(
        floor=floor
    ).select_related("floor", "location")

    results = [
        node_data(node)
        for node in nodes
    ]

    return JsonResponse({
        "success": True,
        "floor_id": floor.id,
        "count": len(results),
        "results": results,
    })


# ============================================================
# INDOOR NAVIGATION API - DIJKSTRA
# ============================================================

@require_POST
def indoor_route_api(request):
    try:
        data = json.loads(request.body or "{}")

        if not isinstance(data, dict):
            return JsonResponse({
                "success": False,
                "error": "Request must contain a JSON object.",
            }, status=400)

        start_node_id = data.get("start_node_id")
        end_node_id = data.get("end_node_id")
        accessible_only = data.get("accessible_only", False)

        if not isinstance(accessible_only, bool):
            return JsonResponse({
                "success": False,
                "error": "accessible_only must be true or false.",
            }, status=400)

        try:
            if (
                isinstance(start_node_id, bool)
                or isinstance(end_node_id, bool)
            ):
                raise ValueError

            start_node_id = int(start_node_id)
            end_node_id = int(end_node_id)

            if start_node_id <= 0 or end_node_id <= 0:
                raise ValueError

        except (TypeError, ValueError):
            return JsonResponse({
                "success": False,
                "error": "Valid start and destination node IDs are required.",
            }, status=400)

        start_node = (
            NavigationNode.objects
            .select_related("floor__building")
            .filter(id=start_node_id)
            .first()
        )

        end_node = (
            NavigationNode.objects
            .select_related("floor__building")
            .filter(id=end_node_id)
            .first()
        )

        if not start_node or not end_node:
            return JsonResponse({
                "success": False,
                "error": "Starting node or destination node was not found.",
            }, status=404)

        building_id = start_node.floor.building_id

        if end_node.floor.building_id != building_id:
            return JsonResponse({
                "success": False,
                "error": "Both nodes must belong to the same building.",
            }, status=400)

        # Retrieve all valid connections in this building.
        edges = NavigationEdge.objects.filter(
            from_node__floor__building_id=building_id,
            to_node__floor__building_id=building_id,
            is_restricted=False,
        ).select_related("from_node", "to_node")

        # Build graph.
        graph = {}

        for edge in edges:
            if accessible_only and not edge.is_accessible:
                continue

            weight = float(edge.distance)

            if not math.isfinite(weight) or weight <= 0:
                continue

            graph.setdefault(edge.from_node_id, []).append(
                (edge.to_node_id, weight)
            )

            if edge.is_bidirectional:
                graph.setdefault(edge.to_node_id, []).append(
                    (edge.from_node_id, weight)
                )

        # Dijkstra algorithm.
        distances = {
            start_node.id: 0.0
        }

        previous = {}

        priority_queue = [
            (0.0, start_node.id)
        ]

        while priority_queue:
            current_distance, current_id = heapq.heappop(
                priority_queue
            )

            if current_distance > distances.get(
                current_id, math.inf
            ):
                continue

            if current_id == end_node.id:
                break

            for neighbour_id, weight in graph.get(
                current_id, []
            ):
                new_distance = current_distance + weight

                if new_distance < distances.get(
                    neighbour_id, math.inf
                ):
                    distances[neighbour_id] = new_distance
                    previous[neighbour_id] = current_id

                    heapq.heappush(
                        priority_queue,
                        (new_distance, neighbour_id),
                    )

        # Check route.
        if end_node.id not in distances:
            return JsonResponse({
                "success": False,
                "error": "No route found between these locations.",
            }, status=404)

        # Reconstruct route.
        route_ids = []
        current_id = end_node.id

        while current_id != start_node.id:
            route_ids.append(current_id)
            current_id = previous.get(current_id)

            if current_id is None:
                return JsonResponse({
                    "success": False,
                    "error": "Could not reconstruct navigation route.",
                }, status=500)

        route_ids.append(start_node.id)
        route_ids.reverse()

        # Retrieve route nodes in the correct order.
        route_nodes = NavigationNode.objects.filter(
            id__in=route_ids
        ).select_related("floor", "location")

        node_lookup = {
            node.id: node
            for node in route_nodes
        }

        ordered_nodes = [
            node_lookup[node_id]
            for node_id in route_ids
            if node_id in node_lookup
        ]

        distance = distances[end_node.id]

        # Convert route into floor-wise segments.
        floor_segments = []

        for node in ordered_nodes:
            floor_id = node.floor_id

            if (
                not floor_segments
                or floor_segments[-1]["floor_id"] != floor_id
            ):
                floor_segments.append({
                    "floor_id": floor_id,
                    "floor_name": node.floor.name,
                    "nodes": [],
                })

            floor_segments[-1]["nodes"].append(
                node_data(node)
            )

        return JsonResponse({
            "success": True,
            "mode": "indoor",
            "algorithm": "Dijkstra",
            "building_id": building_id,
            "start_node_id": start_node.id,
            "end_node_id": end_node.id,
            "distance": round(distance, 2),
            "estimated_time_seconds": round(distance / 1.2),
            "node_count": len(ordered_nodes),
            "nodes": [
                node_data(node)
                for node in ordered_nodes
            ],
            "floor_segments": floor_segments,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON request.",
        }, status=400)

    except (TypeError, ValueError):
        return JsonResponse({
            "success": False,
            "error": "Invalid route parameters.",
        }, status=400)


# ============================================================
# OUTDOOR NAVIGATION API - OPENROUTESERVICE
# ============================================================

@require_POST
def outdoor_route_api(request):
    try:
        data = json.loads(request.body or "{}")

        building_id = data.get("building_id")

        if not building_id:
            return JsonResponse({
                "success": False,
                "error": "Building ID is required.",
            }, status=400)

        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        if not (-90 <= latitude <= 90):
            return JsonResponse({
                "success": False,
                "error": "Invalid latitude.",
            }, status=400)

        if not (-180 <= longitude <= 180):
            return JsonResponse({
                "success": False,
                "error": "Invalid longitude.",
            }, status=400)

        building = get_object_or_404(
            Building,
            id=building_id,
            is_active=True,
        )

        destination = building_coordinates(building)

        destination_lat = destination["latitude"]
        destination_lon = destination["longitude"]

        api_key = getattr(settings, "ORS_API_KEY", "")

        base_url = getattr(
            settings,
            "ORS_BASE_URL",
            "https://api.openrouteservice.org",
        ).rstrip("/")

        if not api_key:
            return JsonResponse({
                "success": False,
                "error": "OpenRouteService API key is not configured.",
            }, status=503)

        url = (
            f"{base_url}/v2/directions/"
            "foot-walking/geojson"
        )

        payload = {
            "coordinates": [
                [longitude, latitude],
                [destination_lon, destination_lat],
            ]
        }

        request_data = json.dumps(payload).encode("utf-8")

        req = Request(
            url,
            data=request_data,
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/geo+json",
            },
            method="POST",
        )

        with urlopen(req, timeout=30) as response:
            route_data = json.loads(
                response.read().decode("utf-8")
            )

        features = route_data.get("features", [])

        if not features:
            return JsonResponse({
                "success": False,
                "error": "No outdoor route was found.",
            }, status=404)

        feature = features[0]
        properties = feature.get("properties", {})
        summary = properties.get("summary", {})

        steps = []

        for segment in properties.get("segments", []):
            for step in segment.get("steps", []):
                steps.append({
                    "instruction": step.get("instruction", ""),
                    "distance": step.get("distance", 0),
                    "duration": step.get("duration", 0),
                    "type": step.get("type"),
                })

        return JsonResponse({
            "success": True,
            "mode": "walking",
            "building": {
                "id": building.id,
                "name": building.name,
                "latitude": destination_lat,
                "longitude": destination_lon,
            },
            "route": {
                "geometry": feature.get("geometry"),
                "distance_meters": summary.get("distance", 0),
                "duration_seconds": summary.get("duration", 0),
                "steps": steps,
            },
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON request.",
        }, status=400)

    except (TypeError, ValueError):
        return JsonResponse({
            "success": False,
            "error": "Invalid GPS coordinates or request data.",
        }, status=400)

    except HTTPError as error:
        error_message = error.read().decode(
            "utf-8",
            errors="replace",
        )

        return JsonResponse({
            "success": False,
            "error": "OpenRouteService rejected the route request.",
            "details": error_message[:500],
        }, status=502)

    except (URLError, TimeoutError, OSError) as error:
        return JsonResponse({
            "success": False,
            "error": "Could not connect to OpenRouteService.",
            "details": str(error),
        }, status=502)


# ============================================================
# QR LOCATION API
# ============================================================

@require_GET
def qr_location_api(request, code):
    qr_location = get_object_or_404(
        QRLocation.objects.select_related(
            "node__floor__building"
        ),
        code=code,
        is_active=True,
    )

    node = qr_location.node

    return JsonResponse({
        "success": True,
        "qr_code": qr_location.code,
        "label": qr_location.label,
        "node": node_data(node),
        "building_id": node.floor.building_id,
        "building_name": node.floor.building.name,
    })


# ============================================================
# OPENSTREETMAP CONFIGURATION
# ============================================================

OSM_SEARCH_URL = getattr(
    settings,
    "OSM_NOMINATIM_SEARCH_URL",
    "https://nominatim.openstreetmap.org/search",
)


# ============================================================
# OPENSTREETMAP REQUEST HELPER
# ============================================================

def osm_request(params):
    cache_key = "osm_search_" + str(
        abs(hash(urlencode(params, doseq=True)))
    )

    cached_result = cache.get(cache_key)

    if cached_result is not None:
        return cached_result

    if not cache.add(
        "osm_nominatim_rate_limit",
        True,
        timeout=1,
    ):
        raise ValueError(
            "Please wait one second before making another OSM search."
        )

    user_agent = getattr(
        settings,
        "OSM_NOMINATIM_USER_AGENT",
        "HybridNavigator/1.0",
    )

    request_url = OSM_SEARCH_URL + "?" + urlencode(params)

    req = Request(
        request_url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=20) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        cache.set(cache_key, result, timeout=3600)
        return result

    except HTTPError as error:
        raise RuntimeError(
            f"OpenStreetMap HTTP error: {error.code}"
        )

    except URLError as error:
        raise RuntimeError(
            f"OpenStreetMap connection error: {error.reason}"
        )

    except (
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        raise RuntimeError(
            f"OpenStreetMap request failed: {str(error)}"
        )


# ============================================================
# OPENSTREETMAP BUILDING SEARCH API
# ============================================================

@require_GET
def osm_building_search_api(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 3:
        return JsonResponse({
            "success": False,
            "error": "Enter at least 3 characters.",
        }, status=400)

    # Supplied Starbucks OSM node.
    if (
        "starbucks" in query.lower()
        or "phoenix marketcity" in query.lower()
    ):
        result = {
            "osm_ref": "node/4447494197",
            "osm_type": "node",
            "osm_id": 4447494197,
            "name": "Starbucks",
            "address": (
                "Phoenix Marketcity, Whitefield Main Road, "
                "Mahadevpura, Bengaluru, Karnataka 560048"
            ),
            "latitude": "12.9977264",
            "longitude": "77.6966474",
            "category": "amenity",
            "type": "cafe",
            "geometry": None,
            "tags": {
                "amenity": "cafe",
                "cuisine": "coffee_shop",
                "level": "0",
                "name": "Starbucks",
            },
        }

        cache.set(
            "osm_import:node/4447494197",
            result,
            timeout=86400,
        )

        return JsonResponse({
            "success": True,
            "source": "OpenStreetMap",
            "attribution": "© OpenStreetMap contributors",
            "query": query,
            "count": 1,
            "results": [result],
        })

    params = {
        "format": "jsonv2",
        "q": query,
        "addressdetails": 1,
        "extratags": 1,
        "namedetails": 1,
        "polygon_geojson": 1,
        "limit": 10,
    }

    try:
        osm_results = osm_request(params)

    except ValueError as error:
        return JsonResponse({
            "success": False,
            "error": str(error),
        }, status=429)

    except RuntimeError as error:
        return JsonResponse({
            "success": False,
            "error": str(error),
        }, status=502)

    results = []

    for item in osm_results:
        osm_type = item.get("osm_type", "")
        osm_id = item.get("osm_id")

        if not osm_type or not osm_id:
            continue

        osm_ref = f"{osm_type}/{osm_id}"

        latitude = item.get("lat")
        longitude = item.get("lon")

        if latitude is None or longitude is None:
            continue

        result = {
            "osm_ref": osm_ref,
            "osm_type": osm_type,
            "osm_id": osm_id,
            "name": (
                item.get("name")
                or item.get(
                    "display_name",
                    "Unnamed place",
                ).split(",")[0]
            ),
            "address": item.get("display_name", ""),
            "latitude": latitude,
            "longitude": longitude,
            "category": item.get("category", ""),
            "type": item.get("type", ""),
            "geometry": item.get("geojson"),
            "tags": item.get("extratags") or {},
        }

        cache.set(
            f"osm_import:{osm_ref}",
            result,
            timeout=86400,
        )

        results.append(result)

    return JsonResponse({
        "success": True,
        "source": "OpenStreetMap",
        "attribution": "© OpenStreetMap contributors",
        "query": query,
        "count": len(results),
        "results": results,
    })


# ============================================================
# OPENSTREETMAP BUILDING TYPE DETECTION
# ============================================================

def detect_building_type(item):
    tags = item.get("tags") or {}

    category = (
        item.get("category") or ""
    ).lower()

    osm_type = (
        item.get("type") or ""
    ).lower()

    if (
        tags.get("amenity") == "hospital"
        or tags.get("healthcare") == "hospital"
        or category == "healthcare"
        or osm_type == "hospital"
    ):
        return Building.BuildingType.HOSPITAL

    if (
        category == "railway"
        or osm_type in ("station", "halt")
        or tags.get("railway") in ("station", "halt")
    ):
        return Building.BuildingType.RAILWAY_STATION

    if (
        category == "aeroway"
        or tags.get("aeroway") in ("aerodrome", "terminal")
    ):
        return Building.BuildingType.AIRPORT

    if (
        tags.get("shop") == "mall"
        or tags.get("amenity") == "mall"
        or osm_type == "mall"
    ):
        return Building.BuildingType.MALL

    if (
        tags.get("amenity") == "university"
        or osm_type == "university"
    ):
        return Building.BuildingType.UNIVERSITY

    return Building.BuildingType.OTHER


# ============================================================
# OPENSTREETMAP BUILDING IMPORT API
# ============================================================

@require_POST
@transaction.atomic
def osm_building_import_api(request):
    try:
        data = json.loads(request.body or "{}")

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON request.",
        }, status=400)

    osm_ref = str(data.get("osm_ref", "")).strip()

    if not osm_ref:
        return JsonResponse({
            "success": False,
            "error": "OSM reference is required.",
        }, status=400)

    item = cache.get(f"osm_import:{osm_ref}")

    # Fallback for the supplied Starbucks OSM node.
    if not item and osm_ref == "node/4447494197":
        item = {
            "osm_ref": "node/4447494197",
            "osm_type": "node",
            "osm_id": 4447494197,
            "name": "Starbucks",
            "address": (
                "Phoenix Marketcity, Whitefield Main Road, "
                "Mahadevpura, Bengaluru, Karnataka 560048"
            ),
            "latitude": "12.9977264",
            "longitude": "77.6966474",
            "category": "amenity",
            "type": "cafe",
            "geometry": None,
            "tags": {
                "amenity": "cafe",
                "cuisine": "coffee_shop",
                "level": "0",
                "name": "Starbucks",
            },
        }

    if not item:
        return JsonResponse({
            "success": False,
            "error": "Search for this OSM result again before importing.",
        }, status=400)

    try:
        latitude = float(item["latitude"])
        longitude = float(item["longitude"])

    except (TypeError, ValueError, KeyError):
        return JsonResponse({
            "success": False,
            "error": "Invalid OSM coordinates.",
        }, status=400)

    if not (
        -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        return JsonResponse({
            "success": False,
            "error": "Coordinates are outside valid ranges.",
        }, status=400)

    name = str(
        item.get("name") or "Unnamed building"
    ).strip()

    if not name:
        name = "Unnamed building"

    address = str(item.get("address") or "")[:255]

    organisation, _ = Organisation.objects.get_or_create(
        slug="openstreetmap-imports",
        defaults={
            "name": "OpenStreetMap Imports",
        },
    )

    existing = Building.objects.filter(
        osm_ref=osm_ref
    ).first()

    if existing:
        name = existing.name

    else:
        original_name = name
        counter = 1

        while Building.objects.filter(
            organisation=organisation,
            name=name,
        ).exists():
            counter += 1
            name = f"{original_name} ({counter})"

    building_type = detect_building_type(item)

    building, created = Building.objects.update_or_create(
        osm_ref=osm_ref,
        defaults={
            "organisation": organisation,
            "name": name,
            "building_type": building_type,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "source": Building.DataSource.OPENSTREETMAP,
            "osm_geometry": item.get("geometry"),
            "osm_tags": item.get("tags") or {},
            "is_active": True,
        },
    )

    # Create a logical Ground Floor only for this supplied node.
    # No indoor locations or navigation nodes are fabricated.
    if osm_ref == "node/4447494197":
        Floor.objects.get_or_create(
            building=building,
            level=0,
            defaults={
                "name": "Ground Floor (OSM level 0)",
                "svg_width": 1000,
                "svg_height": 600,
            },
        )

    return JsonResponse({
        "success": True,
        "message": (
            "Building imported successfully."
            if created
            else "Building updated successfully."
        ),
        "created": created,
        "building": {
            "id": building.id,
            "name": building.name,
            "building_type": building.building_type,
            "address": building.address,
            "latitude": float(building.latitude),
            "longitude": float(building.longitude),
            "osm_ref": building.osm_ref,
            "source": building.source,
        },
    })
