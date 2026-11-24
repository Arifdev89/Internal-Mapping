
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# ==========================================
# ORGANISATION
# ==========================================

class Organisation(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ==========================================
# BUILDING
# ==========================================

class Building(models.Model):

    class BuildingType(models.TextChoices):
        HOSPITAL = "hospital", "Hospital"
        RAILWAY_STATION = "railway_station", "Railway station"
        AIRPORT = "airport", "Airport"
        MALL = "mall", "Shopping mall"
        UNIVERSITY = "university", "University"
        OTHER = "other", "Other"

    class DataSource(models.TextChoices):
        MANUAL = "manual", "Manual"
        OPENSTREETMAP = "openstreetmap", "OpenStreetMap"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="buildings"
    )

    name = models.CharField(max_length=120)

    building_type = models.CharField(
        max_length=20,
        choices=BuildingType.choices,
        default=BuildingType.HOSPITAL
    )

    address = models.CharField(max_length=255, blank=True)

    # Outdoor GPS coordinates
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90)
        ]
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180)
        ]
    )

    # ======================================
    # OPENSTREETMAP INTEGRATION
    # ======================================

    osm_ref = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        help_text="OSM reference, e.g. way/123456"
    )

    source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.MANUAL
    )

    osm_geometry = models.JSONField(
        null=True,
        blank=True,
        help_text="Building footprint in GeoJSON format"
    )

    osm_tags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Original OpenStreetMap tags"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "name"],
                name="unique_building_per_organisation"
            )
        ]

        indexes = [
            models.Index(
                fields=["building_type", "is_active"]
            ),
            models.Index(
                fields=["latitude", "longitude"]
            ),
        ]

    def __str__(self):
        return self.name


# ==========================================
# FLOOR
# ==========================================

class Floor(models.Model):

    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="floors"
    )

    level = models.SmallIntegerField(
        help_text="0 = ground floor, 1 = first floor, -1 = basement"
    )

    name = models.CharField(max_length=60)

    svg_width = models.PositiveIntegerField(default=1000)

    svg_height = models.PositiveIntegerField(default=600)

    meters_per_unit = models.FloatField(
        default=0.1,
        validators=[MinValueValidator(0.001)]
    )

    class Meta:
        ordering = ["building", "level"]

        constraints = [
            models.UniqueConstraint(
                fields=["building", "level"],
                name="unique_floor_level_per_building"
            )
        ]

    def __str__(self):
        return f"{self.building.name} - {self.name}"


# ==========================================
# LOCATION
# ==========================================

class Location(models.Model):

    class Category(models.TextChoices):
        DEPARTMENT = "department", "Department"
        WARD = "ward", "Ward"
        FACILITY = "facility", "Facility"
        ENTRANCE = "entrance", "Entrance"
        TRANSPORT = "transport", "Stairs / Lift"
        SERVICE = "service", "Service area"

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    name = models.CharField(max_length=120, db_index=True)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.DEPARTMENT
    )

    description = models.CharField(max_length=255, blank=True)

    x = models.FloatField()

    y = models.FloatField()

    width = models.FloatField(
        validators=[MinValueValidator(1)]
    )

    height = models.FloatField(
        validators=[MinValueValidator(1)]
    )

    is_restricted = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["floor", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["floor", "name"],
                name="unique_location_name_per_floor"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.floor.name})"


# ==========================================
# NAVIGATION NODE
# ==========================================

class NavigationNode(models.Model):

    class NodeType(models.TextChoices):
        ENTRANCE = "entrance", "Entrance"
        EXIT = "exit", "Exit"
        JUNCTION = "junction", "Corridor junction"
        ROOM = "room", "Room / department"
        STAIRCASE = "staircase", "Staircase"
        LIFT = "lift", "Lift / elevator"
        RAMP = "ramp", "Ramp"
        ESCALATOR = "escalator", "Escalator"
        RESTROOM = "restroom", "Restroom"

    code = models.CharField(
        max_length=40,
        unique=True,
        help_text="Short unique ID, e.g. F1-CAR"
    )

    name = models.CharField(max_length=120)

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="nodes"
    )

    x = models.FloatField()

    y = models.FloatField()

    node_type = models.CharField(
        max_length=12,
        choices=NodeType.choices,
        default=NodeType.JUNCTION
    )

    location = models.OneToOneField(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="node"
    )

    class Meta:
        ordering = ["floor", "code"]

        indexes = [
            models.Index(fields=["floor", "node_type"])
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


# ==========================================
# NAVIGATION EDGE
# ==========================================

class NavigationEdge(models.Model):

    class ConnectionType(models.TextChoices):
        CORRIDOR = "corridor", "Corridor"
        STAIRS = "stairs", "Stairs"
        ELEVATOR = "elevator", "Elevator"
        RAMP = "ramp", "Ramp"
        ESCALATOR = "escalator", "Escalator"
        DOOR = "door", "Door"

    from_node = models.ForeignKey(
        NavigationNode,
        on_delete=models.CASCADE,
        related_name="edges_out"
    )

    to_node = models.ForeignKey(
        NavigationNode,
        on_delete=models.CASCADE,
        related_name="edges_in"
    )

    distance = models.FloatField(
        validators=[MinValueValidator(0.1)],
        help_text="Walking cost in metres"
    )

    connection_type = models.CharField(
        max_length=12,
        choices=ConnectionType.choices,
        default=ConnectionType.CORRIDOR
    )

    is_accessible = models.BooleanField(default=True)

    is_restricted = models.BooleanField(default=False)

    is_bidirectional = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_node", "to_node"],
                name="unique_edge_between_nodes"
            ),
            models.CheckConstraint(
                condition=models.Q(distance__gt=0),
                name="edge_distance_positive"
            ),
        ]

        indexes = [
            models.Index(fields=["connection_type"])
        ]

    def clean(self):

        if self.from_node_id and self.from_node_id == self.to_node_id:
            raise ValidationError(
                "An edge cannot connect a node to itself."
            )

    @property
    def is_floor_transition(self):
        return self.from_node.floor_id != self.to_node.floor_id

    def __str__(self):
        return (
            f"{self.from_node.code} -> "
            f"{self.to_node.code} ({self.connection_type})"
        )


# ==========================================
# BUILDING ENTRANCE
# ==========================================

class Entrance(models.Model):

    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="entrances"
    )

    name = models.CharField(max_length=120)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    node = models.ForeignKey(
        NavigationNode,
        on_delete=models.CASCADE,
        related_name="entrances"
    )

    is_main = models.BooleanField(default=False)

    class Meta:
        ordering = ["building", "-is_main", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["building", "name"],
                name="unique_entrance_per_building"
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.building.name}"


# ==========================================
# INDOOR BEACON
# ==========================================

class IndoorBeacon(models.Model):

    label = models.CharField(max_length=120)

    uuid = models.UUIDField()

    major = models.PositiveIntegerField(
        validators=[MaxValueValidator(65535)]
    )

    minor = models.PositiveIntegerField(
        validators=[MaxValueValidator(65535)]
    )

    node = models.ForeignKey(
        NavigationNode,
        on_delete=models.CASCADE,
        related_name="beacons"
    )

    tx_power = models.SmallIntegerField(default=-59)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label"]

        constraints = [
            models.UniqueConstraint(
                fields=["uuid", "major", "minor"],
                name="unique_beacon_identity"
            )
        ]

    def __str__(self):
        return f"{self.label} ({self.major}/{self.minor})"


# ==========================================
# QR LOCATION
# ==========================================

class QRLocation(models.Model):

    code = models.CharField(max_length=60, unique=True)

    label = models.CharField(max_length=120)

    node = models.ForeignKey(
        NavigationNode,
        on_delete=models.CASCADE,
        related_name="qr_codes"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} -> {self.node.code}"


# ==========================================
# NAVIGATION HISTORY
# ==========================================

class NavigationHistory(models.Model):

    class Mode(models.TextChoices):
        INDOOR = "indoor", "Indoor"
        OUTDOOR = "outdoor", "Outdoor"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="navigation_history"
    )

    session_key = models.CharField(max_length=64, blank=True)

    building = models.ForeignKey(
        Building,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="navigation_history"
    )

    mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        default=Mode.INDOOR
    )

    start_node = models.ForeignKey(
        NavigationNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )

    end_node = models.ForeignKey(
        NavigationNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )

    accessible_only = models.BooleanField(default=False)

    distance_m = models.FloatField(default=0)

    duration_s = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.STARTED
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        verbose_name_plural = "navigation history"

        indexes = [
            models.Index(fields=["session_key", "created_at"])
        ]

    def __str__(self):
        return f"{self.mode} trip #{self.pk} ({self.status})"
