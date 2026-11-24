from django.contrib import admin

from .models import (
    Building,
    Entrance,
    Floor,
    IndoorBeacon,
    Location,
    NavigationEdge,
    NavigationHistory,
    NavigationNode,
    Organisation,
    QRLocation,
)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class FloorInline(admin.TabularInline):
    model = Floor
    extra = 0


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "organisation", "building_type", "latitude", "longitude", "is_active")
    list_filter = ("building_type", "is_active", "organisation")
    search_fields = ("name", "address")
    inlines = [FloorInline]


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "level", "svg_width", "svg_height", "meters_per_unit")
    list_filter = ("building",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "floor", "category", "is_restricted", "is_active")
    list_filter = ("floor__building", "floor", "category", "is_restricted", "is_active")
    search_fields = ("name", "description")
    list_select_related = ("floor", "floor__building")


@admin.register(NavigationNode)
class NavigationNodeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "floor", "node_type", "x", "y")
    list_filter = ("floor__building", "floor", "node_type")
    search_fields = ("code", "name")
    list_select_related = ("floor",)


@admin.register(NavigationEdge)
class NavigationEdgeAdmin(admin.ModelAdmin):
    list_display = (
        "from_node",
        "to_node",
        "distance",
        "connection_type",
        "is_accessible",
        "is_restricted",
        "is_bidirectional",
    )
    list_filter = ("connection_type", "is_accessible", "is_restricted", "from_node__floor")
    search_fields = ("from_node__code", "to_node__code")
    autocomplete_fields = ("from_node", "to_node")
    list_select_related = ("from_node", "to_node")


@admin.register(Entrance)
class EntranceAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "latitude", "longitude", "node", "is_main")
    list_filter = ("building", "is_main")
    autocomplete_fields = ("node",)


@admin.register(IndoorBeacon)
class IndoorBeaconAdmin(admin.ModelAdmin):
    list_display = ("label", "uuid", "major", "minor", "node", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label",)
    autocomplete_fields = ("node",)


@admin.register(QRLocation)
class QRLocationAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "node", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "label")
    autocomplete_fields = ("node",)


@admin.register(NavigationHistory)
class NavigationHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "mode", "building", "start_node", "end_node", "status", "created_at")
    list_filter = ("mode", "status", "accessible_only")
    readonly_fields = [f.name for f in NavigationHistory._meta.fields]

    def has_add_permission(self, request):
        return False
