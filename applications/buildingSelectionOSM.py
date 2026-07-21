"""Interactive OSM building-selection widget for Jupyter notebooks.

Usage in a notebook:

    from applications.buildingSelectionOSM import mapOSM
    mapOSM

The most recently drawn geometries are available as:

    app.poly_coords_ll
    app.poly_geojson
    app.polygon_coords_ll
    app.polygon_geojson
"""

from IPython.display import display
from ipyleaflet import DrawControl, Map, TileLayer
from ipywidgets import Button, HTML, VBox
from ipywidgets import Layout

class MapOSM:
    """Interactive map that stores the latest polyline and polygon selection."""

    def __init__(
        self,
        center=(52.532461318193775, 13.422214655200957),
        zoom=17,
    ):
        self.poly_coords_ll = []
        self.poly_geojson = None
        self.polygon_coords_ll = []
        self.polygon_geojson = None

        self.info = HTML(
            "Please draw a <b>Polyline</b> or a <b>Polygon</b>. "
            "Click to define coordinates; <b>double-click</b> to finish a "
            "polyline or close the polygon."
        )


        self.map = Map(
            center=center,
            zoom=zoom,
            scroll_wheel_zoom=True,
            layout=Layout(
                width="100%",
                height=f"800px"),
        )
        self.map.add_layer(
            TileLayer(
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                name="OSM",
            )
        )

        self.draw = DrawControl(
            polyline={"shapeOptions": {"weight": 4}},
            polygon={"shapeOptions": {"weight": 4}},
        )
        self.draw.circle = {}
        self.draw.rectangle = {}
        self.draw.marker = {}
        self.draw.circlemarker = {}
        self.draw.on_draw(self._handle_draw)
        self.map.add_control(self.draw)

        self.reset_button = Button(
            description="Clear building selection",
            icon="trash",
            button_style="warning",
            tooltip="Delete all drawn shapes and saved coordinates",
        )
        self.reset_button.on_click(self.reset_selection)

        self.widget = VBox([self.map, self.reset_button, self.info])

    def _handle_draw(self, *args, **kwargs):
        """Store the most recently drawn polyline or polygon."""
        # ipyleaflet versions use either (action, geo_json) or
        # (target, action, geo_json) for DrawControl callbacks.
        if len(args) == 2:
            _, geo_json = args
        elif len(args) == 3:
            _, _, geo_json = args
        else:
            geo_json = kwargs.get("geo_json")

        if not geo_json:
            return

        geometry = geo_json.get("geometry", {})
        geometry_type = geometry.get("type")

        if geometry_type == "LineString":
            self.poly_geojson = geo_json
            self.poly_coords_ll = geometry.get("coordinates", [])
            self.info.value = (
                f"<b>Polyline defined:</b> "
                f"{len(self.poly_coords_ll)} points."
            )
        elif geometry_type == "Polygon":
            rings = geometry.get("coordinates", [])
            if rings:
                self.polygon_geojson = geo_json
                self.polygon_coords_ll = rings[0]
                self.info.value = (
                    f"<b>Polygon defined:</b> "
                    f"{len(self.polygon_coords_ll)} points."
                )
            else:
                self.info.value = "Received an empty polygon."
        else:
            self.info.value = (
                "Please draw a <b>Polyline</b> or a <b>Polygon</b>."
            )

    def reset_selection(self, _button=None):
        """Clear stored geometry data and remove drawings from the map."""
        self.poly_coords_ll = []
        self.poly_geojson = None
        self.polygon_coords_ll = []
        self.polygon_geojson = None

        # Remove all visible geometries managed by the DrawControl.
        self.draw.clear()

        self.info.value = (
            "Selection reset. Please draw a <b>Polyline</b> or a "
            "<b>Polygon</b>."
        )

    def _ipython_display_(self):
        """Display the widget when ``app`` is the final notebook expression."""
        display(self.widget)


mapOSM = MapOSM()
