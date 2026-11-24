
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    # Database status
    path(
        "api/status/database/",
        views.database_status_api,
        name="database_status_api",
    ),

    # Buildings
    path(
        "api/buildings/",
        views.building_list_api,
        name="building_list_api",
    ),

    # Place search
    path(
        "api/places/search/",
        views.search_places,
        name="search_places",
    ),

    # Building floors
    path(
        "api/buildings/<int:building_id>/floors/",
        views.building_floors_api,
        name="building_floors_api",
    ),

    # Floor locations
    path(
        "api/floors/<int:floor_id>/locations/",
        views.floor_locations_api,
        name="floor_locations_api",
    ),

    # Floor navigation nodes
    path(
        "api/floors/<int:floor_id>/nodes/",
        views.floor_nodes_api,
        name="floor_nodes_api",
    ),

    # Indoor navigation
    path(
        "api/indoor/route/",
        views.indoor_route_api,
        name="indoor_route_api",
    ),

    # QR location
    path(
        "api/qr/<str:code>/",
        views.qr_location_api,
        name="qr_location_api",
    ),

    # OpenStreetMap building search
    path(
        "api/osm/buildings/search/",
        views.osm_building_search_api,
        name="osm_building_search_api",
    ),

    # OpenStreetMap building import
    path(
        "api/osm/buildings/import/",
        views.osm_building_import_api,
        name="osm_building_import_api",
    ),

    # Outdoor navigation
    path(
        "api/outdoor/route/",
        views.outdoor_route_api,
        name="outdoor_route_api",
    ),

path(
    "api/indoor/route/",
    views.indoor_route_api,
    name="indoor_route_api",
),

path(
    "api/floors/<int:floor_id>/nodes/",
    views.floor_nodes_api,
    name="floor_nodes_api",
),

]
