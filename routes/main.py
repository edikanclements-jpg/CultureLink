"""Homepage and the public locations of the curated boutiques."""

from math import atan2, degrees, hypot

from flask import Blueprint, render_template

from services.boutiques import get_all_boutiques
from services.catalog_rules import LOCATION_OVERRIDES


main_bp = Blueprint("main", __name__)

# City or country centers, as listed in the catalog. Offsets separate nearby pins.
_MAP_LOCATIONS = {
    1: (19.03, 73.03, -7, 23),
    2: (32.78, -96.80, -20, -20),
    5: (28.46, 77.03, 21, -17),
    6: (29.76, -95.37, 21, 19),
    7: (9.08, 8.68, -6, 10),
    8: (54.50, -2.50, 1, -10),
}


def _map_pins(boutiques):
    pins = []
    for boutique in boutiques:
        identifier = boutique["boutique_id"]
        if identifier not in _MAP_LOCATIONS:
            continue
        name, location = LOCATION_OVERRIDES[identifier]
        if boutique["boutique_name"].strip().casefold() != name.casefold() or boutique["location"] != location:
            continue
        latitude, longitude, dx, dy = _MAP_LOCATIONS[identifier]
        pins.append(dict(
            id=identifier, number=len(pins) + 1, name=name, location=location,
            x=round((longitude + 180) / 3.6, 3),
            y=round((84 - latitude) / 1.54, 3),
            dx=dx, dy=dy, leader=round(hypot(dx, dy), 2),
            angle=round(degrees(atan2(dy, dx)), 2),
        ))
    return pins


@main_bp.route("/")
def home():
    boutiques = get_all_boutiques()
    return render_template("index.html", boutiques=boutiques, map_pins=_map_pins(boutiques))
