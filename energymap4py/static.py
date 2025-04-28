import requests
import json

# global test variables
test_uuid = 'DEBE04YY500002vO'
test_lon = 13.467488494175514
test_lat = 52.50587905804428
test_line = [(13.324412829321979, 52.516957033745285),(13.322429034685205, 52.514576803927426),(13.322485599381766, 52.51321707446597)]
test_poly = [(13.322027104721627, 52.51773514881992),(13.321124828370177, 52.516709837521866),(13.323525466163757, 52.51597401976454),(13.324266491874166, 52.5169650913811),(13.322847600680866, 52.517782208350184)]

# global api url
# api_url = 'http://localhost:3000'
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

def by_uuid(uuid=test_uuid):
    url = '{}/query?mode=uuid&uuid={}'.format(api_url, uuid)
    print(url)
    return get_response(url)

def by_point(lon=test_lon, lat=test_lat, dist=0):
    """
    Calls the EnergyMap API to retrieve buildings near a point.

    :param lon: Longitude of the point in EPSG25833
    :type lon: float
    :param lat: Latitude of the point in EPSG25833
    :type lat: float
    :param dist: Maximum distance from the point in meters
    :type dist: int
    :return: JSON response
    """
    url = '{}/query?mode=point&longitude={}&latitude={}&distance={}'.format(api_url, lon, lat, dist)
    # Print the URL to the console for debugging
    print(url)
    return get_response(url)

def by_line(line_points=test_line, dist=0):
    """
    Calls the EnergyMap API to retrieve buildings along a line.

    :param line_points: List of points defining the line
    :type line_points: list of (float, float)
    :param dist: Maximum distance from the line in meters
    :type dist: int
    :return: JSON response
    """
    url = f"{api_url}/query?mode=line&linestring="  # Add the URL parameters
    for point in line_points:  # Iterate over the line points
        url += f"{point[0]},{point[1]},"  # Add the point coordinates to the URL
    url = url[:-1]  # Remove the last ',' character
    url += f"&distance={dist}"
    print(url)
    return get_response(url)

def by_polygon(polygon_points=test_poly):
    """
    Calls the EnergyMap API to retrieve buildings within a polygon.

    :param polygon_points: List of points defining the polygon
    :type polygon_points: list of (float, float)
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
    return get_response(url)
