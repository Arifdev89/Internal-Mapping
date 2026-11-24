"""
Read-only JSON APIs that feed the indoor floor-plan page.

GET /api/buildings/                         all active buildings
GET /api/buildings/<id>/floors/             floors of one building
GET /api/buildings/<id>/locations/?q=       searchable rooms of one building
GET /api/floors/<id>/map/                   everything needed to draw one floor
GET /api/floors/<id>/locations/             rooms on one floor
"""
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Building, Floor, Location, NavigationEdge, NavigationNode


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


def _floor_dict(floor):
    return {
        "id": floor.id,
        "building_id": floor.building_id,
        "level": floor.level,
        "name": floor.name,
        "svg_width": floor.svg_width,
        "svg_height": floor.svg_height,
        "meters_per_unit": floor.meters_per_unit,
    }


def _location_dict(location, node_code):
    return {
        "id": location.id,
        "floor_id": location.floor_id,
        "name": location.name,
        "category": location.category,
        "description": location.description,
        "x": location.x,
        "y": location.y,
        "width": location.width,
        "height": location.height,
        "is_restricted": location.is_restricted,
        "node_code": node_code,
    }


def _get_building(building_id):
    return Building.objects.filter(pk=building_id, is_active=True).first()


@require_GET
def buildings(request):
    items = (
        Building.objects.filter(is_active=True)
        .select_related("organisation")
        .annotate(floor_count=Count("floors"))
        .order_by("name")
    )
    return JsonResponse({
        "buildings": [
            {
                "id": b.id,
                "name": b.name,
                "type": b.building_type,
                "address": b.address,
                "latitude": float(b.latitude),
                "longitude": float(b.longitude),
                "organisation": b.organisation.name,
                "floor_count": b.floor_count,
            }
            for b in items
        ]
    })


@require_GET
def building_floors(request, building_id):
    building = _get_building(building_id)
    if building is None:
        return _error("Building not found.", 404)
    floors = Floor.objects.filter(building=building).order_by("level")
    return JsonResponse({
        "building": {"id": building.id, "name": building.name},
        "floors": [_floor_dict(f) for f in floors],
    })


@require_GET
def building_locations(request, building_id):
    building = _get_building(building_id)
    if building is None:
        return _error("Building not found.", 404)

    query = request.GET.get("q", "").strip()
    if len(query) > 80:
        return _error("Search text is too long.", 400)

    locations = (
        Location.objects.filter(floor__building=building, is_active=True)
        .select_related("floor")
        .order_by("floor__level", "name")
    )
    if query:
        locations = locations.filter(name__icontains=query)

    node_codes = dict(
        NavigationNode.objects.filter(
            floor__building=building, location__isnull=False
        ).values_list("location_id", "code")
    )

    results = []
    for location in locations[:200]:
        item = _location_dict(location, node_codes.get(location.id))
        item["floor_level"] = location.floor.level
        item["floor_name"] = location.floor.name
        results.append(item)
    return JsonResponse({"locations": results})


@require_GET
def floor_locations(request, floor_id):
    floor = Floor.objects.filter(pk=floor_id, building__is_active=True).first()
    if floor is None:
        return _error("Floor not found.", 404)

    node_codes = dict(
        NavigationNode.objects.filter(floor=floor, location__isnull=False)
        .values_list("location_id", "code")
    )
    locations = Location.objects.filter(floor=floor, is_active=True).order_by("name")
    return JsonResponse({
        "floor": _floor_dict(floor),
        "locations": [_location_dict(l, node_codes.get(l.id)) for l in locations],
    })


@require_GET
def floor_map(request, floor_id):
    """Rooms, graph nodes, walkable edges, and links to other floors for one floor."""
    floor = Floor.objects.filter(pk=floor_id, building__is_active=True).first()
    if floor is None:
        return _error("Floor not found.", 404)

    nodes = list(NavigationNode.objects.filter(floor=floor).order_by("code"))
    node_codes = {n.location_id: n.code for n in nodes if n.location_id}
    locations = Location.objects.filter(floor=floor, is_active=True).order_by("name")

    # Edges that start and end on this floor are drawn as corridors.
    # Edges that reach another floor become "connections" (lift / stairs links).
    edges = []
    connections = []
    touching = (
        NavigationEdge.objects.filter(Q(from_node__floor=floor) | Q(to_node__floor=floor))
        .select_related("from_node__floor", "to_node__floor")
    )
    for edge in touching:
        from_here = edge.from_node.floor_id == floor.id
        to_here = edge.to_node.floor_id == floor.id
        if from_here and to_here:
            edges.append({
                "from": edge.from_node.code,
                "to": edge.to_node.code,
                "distance": edge.distance,
                "connection_type": edge.connection_type,
                "is_accessible": edge.is_accessible,
                "is_restricted": edge.is_restricted,
            })
            continue

        if from_here:
            here, there = edge.from_node, edge.to_node
        elif edge.is_bidirectional:
            here, there = edge.to_node, edge.from_node
        else:
            continue
        connections.append({
            "node_code": here.code,
            "to_node_code": there.code,
            "to_floor_id": there.floor_id,
            "to_floor_level": there.floor.level,
            "to_floor_name": there.floor.name,
            "connection_type": edge.connection_type,
            "is_accessible": edge.is_accessible,
            "is_restricted": edge.is_restricted,
        })

    return JsonResponse({
        "floor": _floor_dict(floor),
        "locations": [_location_dict(l, node_codes.get(l.id)) for l in locations],
        "nodes": [
            {
                "code": n.code,
                "name": n.name,
                "x": n.x,
                "y": n.y,
                "node_type": n.node_type,
                "location_id": n.location_id,
            }
            for n in nodes
        ],
        "edges": edges,
        "connections": connections,
    })
