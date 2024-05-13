import requests
import json

# global test variables
test_lon = 13.467488494175514
test_lat = 52.50587905804428
test_line = [(13.324412829321979, 52.516957033745285),(13.322429034685205, 52.514576803927426),(13.322485599381766, 52.51321707446597)]
test_poly = [(13.322027104721627, 52.51773514881992),(13.321124828370177, 52.516709837521866),(13.323525466163757, 52.51597401976454),(13.324266491874166, 52.5169650913811),(13.322847600680866, 52.517782208350184)]

# global api url
api_url = 'http://192.168.42.24:3000'

def get_response(url):
    try:
        r = requests.get(url)
        r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return json.loads(r.text)
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"An error occurred: {e}")
        return {}

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
    url = api_url + '/bldgbypoint/' + str(lon) + '&' + str(lat) + '&' + str(dist)
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
    url = f"{api_url}/bldgbyline/{dist}&"  # Add the URL parameters
    for point in line_points:  # Iterate over the line points
        url += f"{point[0]}&{point[1]}&"  # Add the point coordinates to the URL
    url = url[:-1]  # Remove the last '&' character
    print(url)
    return get_response(url)
