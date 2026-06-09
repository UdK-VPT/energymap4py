"""
data_access.py provides access to the EnergyMap Berlin publication database.
Various funtions give provide different ways to select buildings.
Possible is selection by uuid, by point and distance to point, by polyline or by polygon.
All functions return a test dataset, when no arguments are given when calling the function.
"""

import requests
import json
from datetime import datetime

# global test variables
test_uuid = 'DEBE04YY500002vO'
test_lon = 13.467488494175514
test_lat = 52.50587905804428
test_line = [(13.324412829321979, 52.516957033745285),(13.322429034685205, 52.514576803927426),(13.322485599381766, 52.51321707446597)]
test_poly = [(13.322027104721627, 52.51773514881992),(13.321124828370177, 52.516709837521866),(13.323525466163757, 52.51597401976454),(13.324266491874166, 52.5169650913811),(13.322847600680866, 52.517782208350184)]

# global api url
api_url = 'https://energymap-berlin.de/map'


def get_response(url):
    """
    Sends a GET request to the given URL and returns the response as a JSON object.
    
    :param url: The URL to send the request to.
    :type url: str
    :return: The response as a JSON object, or an empty dictionary if an error occurred.
    :rtype: dict
    """
    try:
        # Send a GET request to the URL
        r = requests.get(url)
        # Raise an exception for bad status codes (4xx or 5xx)
        r.raise_for_status()
        if len(r.json()) > 249:
            print('EnergyMap limits data requests to 250 buildings. Your request was truncated accordingly!')
        # Return the response as a JSON object
        return json.loads(r.text)
    # Handle exceptions
    except (requests.RequestException, json.JSONDecodeError) as e:
        # Print the error message
        print(f"An error occurred: {e}")
        # Return an empty dictionary
        return {}

def added_details_by_uuid(uuid=test_uuid):
    """
    Calls the EnergyMap API to retrieve a building's available geometry data
    and additional performance data for the specified UUID.

    :param uuid: UUID as defined in the Berlin ALKIS system
    :type uuid: string
    :return: JSON response
    """

    url = '{}/query?mode=modeldefault&uuids={}'.format(api_url, uuid)
    print(url)
    return get_response(url)

def _as_list(response):
    """
    Returns an API response as a list of building dictionaries.
    """

    if isinstance(response, list):
        return response
    if isinstance(response, dict) and response:
        return [response]
    return []

def _extract_uuids(response):
    """
    Extracts building UUIDs from an API response.
    """

    return [building["uuid"] for building in _as_list(response) if "uuid" in building]

def _first_response_item(response):
    """
    Returns the first item from a response list, or the response itself.
    """

    if isinstance(response, list):
        return response[0] if response else {}
    return response

def _add_optional_outputs(response, added_details=False, citygml=False, output_file=None):
    """
    Adds optional per-building details and CityGML file access to an API response.
    """

    if not added_details and not citygml:
        return response

    buildings = _as_list(response)
    uuids = _extract_uuids(buildings)
    citygml_file = citygml_by_uuid(uuids, output_file=output_file) if citygml and uuids else None

    for building in buildings:
        uuid = building.get("uuid")
        if added_details and uuid:
            building["added_details"] = _first_response_item(added_details_by_uuid(uuid))
        if citygml:
            building["citygml_file"] = citygml_file

    return response

def by_uuid(uuid=test_uuid, added_details=False, citygml=False, output_file=None):
    """
    Calls the EnergyMap API to retrieve a building with the specified UUID.

    :param uuid: UUID as defined in the Berlin ALKIS system
    :type uuid: string
    :param added_details: If True, add detailed building data to the response
    :type added_details: bool
    :param citygml: If True, download CityGML data and add the file path to the response
    :type citygml: bool
    :param output_file: Path where the CityGML file should be saved
    :type output_file: str
    :return: JSON response
    """
    url = '{}/query?mode=uuid&uuid={}'.format(api_url, uuid)
    print(url)
    response = get_response(url)
    return _add_optional_outputs(response, added_details, citygml, output_file)

def by_point(lon=test_lon, lat=test_lat, dist=0, added_details=False, citygml=False, output_file=None):
    """
    Calls the EnergyMap API to retrieve buildings near a point.

    :param lon: Longitude of the point in EPSG25833
    :type lon: float
    :param lat: Latitude of the point in EPSG25833
    :type lat: float
    :param dist: Maximum distance from the point in meters
    :type dist: int
    :param added_details: If True, add detailed building data to the response
    :type added_details: bool
    :param citygml: If True, download CityGML data and add the file path to the response
    :type citygml: bool
    :param output_file: Path where the CityGML file should be saved
    :type output_file: str
    :return: JSON response
    """
    url = '{}/query?mode=point&longitude={}&latitude={}&distance={}'.format(api_url, lon, lat, dist)
    # Print the URL to the console for debugging
    print(url)
    response = get_response(url)
    return _add_optional_outputs(response, added_details, citygml, output_file)

def by_line(line_points=test_line, dist=0, added_details=False, citygml=False, output_file=None):
    """
    Calls the EnergyMap API to retrieve buildings along a line.

    :param line_points: List of points defining the line
    :type line_points: list of (float, float)
    :param dist: Maximum distance from the line in meters
    :type dist: int
    :param added_details: If True, add detailed building data to the response
    :type added_details: bool
    :param citygml: If True, download CityGML data and add the file path to the response
    :type citygml: bool
    :param output_file: Path where the CityGML file should be saved
    :type output_file: str
    :return: JSON response
    """
    url = f"{api_url}/query?mode=line&linestring="  # Add the URL parameters
    for point in line_points:  # Iterate over the line points
        url += f"{point[0]},{point[1]},"  # Add the point coordinates to the URL
    url = url[:-1]  # Remove the last ',' character
    url += f"&distance={dist}"
    print(url)
    response = get_response(url)
    return _add_optional_outputs(response, added_details, citygml, output_file)

def by_polygon(polygon_points=test_poly, added_details=False, citygml=False, output_file=None):
    """
    Calls the EnergyMap API to retrieve buildings within a polygon.

    :param polygon_points: List of points defining the polygon
    :type polygon_points: list of (float, float)
    :param added_details: If True, add detailed building data to the response
    :type added_details: bool
    :param citygml: If True, download CityGML data and add the file path to the response
    :type citygml: bool
    :param output_file: Path where the CityGML file should be saved
    :type output_file: str
    :return: JSON response
    """
    # Add the URL parameters
    url = f"{api_url}/query?mode=polygon&linestring="
    # Iterate over the polygon points
    for point in polygon_points:
        # Add the point coordinates to the URL
        url += f"{point[0]},{point[1]},"
    # Remove the last ',' character
    url = url[:-1]
    # Print the URL to the console for debugging
    print(url)
    # Call the EnergyMap API and return the response
    response = get_response(url)
    return _add_optional_outputs(response, added_details, citygml, output_file)

def citygml_by_uuid(ids, output_file=None):
    """
    Downloads a CityGML export file for the specified building UUIDs.

    :param ids: UUIDs as defined in the Berlin ALKIS system
    :type ids: list[str] or str
    :param output_file: Path where the downloaded file should be saved.
        If None, the filename is generated from the UUID or current date and time.
    :type output_file: str
    :return: Path to the downloaded file, or None if an error occurred
    """

    if isinstance(ids, str):
        ids = [ids]

    if output_file is None:
        if len(ids) == 1:
            output_file = f"{ids[0]}.zip"
        else:
            output_file = f"citygml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    url = f"{api_url}/api/citygml/export/by-bldg-uuid"
    params = [("ids", uuid) for uuid in ids]

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()

        with open(output_file, "wb") as f:
            f.write(r.content)

        print(r.url)
        return output_file

    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None
