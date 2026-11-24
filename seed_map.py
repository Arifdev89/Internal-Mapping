from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from navigator import seed_data as data
from navigator.models import (
    Building,
    Entrance,
    Floor,
    IndoorBeacon,
    Location,
    NavigationEdge,
    NavigationNode,
    Organisation,
    QRLocation,
)


def _dec(value):
    """Convert a float to a Decimal with 6 decimal places (for GPS fields)."""
    return Decimal(str(round(value, 6)))


class Command(BaseCommand):
    help = "Loads the sample hospital (3 floors, rooms, graph, QR codes, beacons)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lat", type=float, default=12.9716,
            help="Latitude of the hospital's main entrance (default: central Bengaluru)",
        )
        parser.add_argument(
            "--lng", type=float, default=77.5946,
            help="Longitude of the hospital's main entrance",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete the existing sample hospital and create it again",
        )

    def handle(self, *args, **options):
        lat, lng = options["lat"], options["lng"]
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise CommandError("--lat must be -90..90 and --lng must be -180..180.")

        slug = data.ORGANISATION["slug"]
        exists = Organisation.objects.filter(slug=slug).exists()
        if exists and not options["reset"]:
            self.stdout.write(self.style.WARNING(
                "Sample data already exists. Run with --reset to rebuild it."
            ))
            return

        with transaction.atomic():
            if exists:
                Organisation.objects.filter(slug=slug).delete()
            counts = self._seed(lat, lng)

        self.stdout.write(self.style.SUCCESS("Sample hospital created:"))
        for label, number in counts.items():
            self.stdout.write(f"  {label}: {number}")

    def _seed(self, lat, lng):
        organisation = Organisation.objects.create(**data.ORGANISATION)
        building = Building.objects.create(
            organisation=organisation,
            latitude=_dec(lat),
            longitude=_dec(lng),
            **data.BUILDING,
        )

        floors = {}
        for level, name in data.FLOORS:
            floors[level] = Floor.objects.create(
                building=building,
                level=level,
                name=name,
                svg_width=data.SVG_WIDTH,
                svg_height=data.SVG_HEIGHT,
                meters_per_unit=data.METERS_PER_UNIT,
            )

        locations = {}
        for place in data.PLACES:
            x, y, width, height = place["rect"]
            locations[place["code"]] = Location.objects.create(
                floor=floors[place["level"]],
                name=place["name"],
                category=place["category"],
                description=place["description"],
                x=x, y=y, width=width, height=height,
                is_restricted=place["restricted"],
            )

        nodes = {}
        for item in data.NODES:
            nodes[item["code"]] = NavigationNode.objects.create(
                code=item["code"],
                name=item["name"],
                floor=floors[item["level"]],
                x=item["x"],
                y=item["y"],
                node_type=item["node_type"],
                location=locations.get(item["code"]),
            )

        for edge in data.EDGES:
            NavigationEdge.objects.create(
                from_node=nodes[edge["from"]],
                to_node=nodes[edge["to"]],
                distance=edge["distance"],
                connection_type=edge["connection_type"],
                is_accessible=edge["accessible"],
                is_restricted=edge["restricted"],
                is_bidirectional=True,
            )

        for item in data.ENTRANCES:
            Entrance.objects.create(
                building=building,
                name=item["name"],
                latitude=_dec(lat + item["dlat"]),
                longitude=_dec(lng + item["dlng"]),
                node=nodes[item["node"]],
                is_main=item["is_main"],
            )

        for code, label, node_code in data.QR_CODES:
            QRLocation.objects.create(code=code, label=label, node=nodes[node_code])

        for label, major, minor, node_code in data.BEACONS:
            IndoorBeacon.objects.create(
                label=label,
                uuid=data.BEACON_UUID,
                major=major,
                minor=minor,
                node=nodes[node_code],
            )

        return {
            "Floors": len(floors),
            "Locations": len(locations),
            "Navigation nodes": len(nodes),
            "Navigation edges": len(data.EDGES),
            "Entrances": len(data.ENTRANCES),
            "QR codes": len(data.QR_CODES),
            "Beacons": len(data.BEACONS),
        }
