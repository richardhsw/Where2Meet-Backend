from collections import OrderedDict
import debug
import requests



PLACES_API   = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_API  = "https://maps.googleapis.com/maps/api/place/details/json"
DISTANCE_API = "https://maps.googleapis.com/maps/api/distancematrix/json"
API_KEY      = "INSERT_KEY_HERE"


class PlacesError(Exception):
    pass



# ----- DISTANCE MATRIX FUNCTIONS ----- 
def distanceApiCall(key, orig_lng, orig_lat, dest_lng, dest_lat):
    COORDS_FORMAT = "{},{}"
    params = {"key": key, "origins": COORDS_FORMAT.format(orig_lat, orig_lng),
              "destinations": COORDS_FORMAT.format(dest_lat, dest_lng),
              "units": "imperial"}

    r = requests.get(url = DISTANCE_API, params = params)
    data = r.json()

    if len(data["rows"]) > 0:
        try:
            return data["rows"][0]["elements"][0]["distance"]
        except KeyError:
            return {"text": "NA", "value": "NA"}
    else:
        return {"text": "NA", "value": "NA"}


# ----- PLACES DETAILS FUNCTIONS -----
def detailsApiCall(key, place_id, fields):
    """
    Arguments: 
        - key     : API key
        - place_id: unique google id of a place
        - fields  : a list of JSON keys to filter from the result

    Result: 
        string
    """
    params  = {"key": key, "place_id": place_id}

    r = requests.get(url = DETAILS_API, params = params)
    data = r.json()

    result = dict()
    for field in fields:
        if field in data["result"]:
            result[field] = data["result"][field]
        else:
            result[field] = "NA"

    return result

def getHours(places):
    """
    For each place in places, extract the opening hours. 
    """
    results = dict()
    for place in places:
        place_id = place["place_id"]
        details = detailsApiCall(API_KEY, place_id, ["opening_hours"])

        # extracting sunday value
        # TODO: change how extraction works
        if details["opening_hours"] != "NA":
            periods = details["opening_hours"]["periods"]

            if len(periods) != 0 and len(periods[0]) == 2:
                monday_hours = periods[0]
                hours_range = {"open": monday_hours["open"]["time"],
                               "close": monday_hours["close"]["time"]}
                results[place_id] = hours_range
            else:
                results[place_id] = "NA"
        else:
            results[place_id] = "NA"

    return results

def getPlacesDetails(places, **req_data):
    """
    Places is a list of 3-tuples (places_id, scores, votes).
    """
    results = OrderedDict()
    orig_lng = req_data["lng"]
    orig_lat = req_data["lat"]

    for place in places:
        place_id = place[0]
        details = detailsApiCall(API_KEY, place_id, ["formatted_address", "name",
            "rating", "types", "price_level", "photos", "geometry"])

        dest_lng = details["geometry"]["location"]["lng"]
        dest_lat = details["geometry"]["location"]["lat"]
        distance = distanceApiCall(API_KEY, orig_lng, orig_lat, dest_lng, dest_lat)

        results[place_id] = {"votes": str(place[2]), "distance": distance}
        results[place_id].update(details)

    return results


# ----- PLACES SEARCH FUNCTIONS -----

def searchApiCall(key, longi, lat, radius=16000, keyword=None, minPrice=None,
                  maxPrice=None, openNow=None, rankBy=None, placeType=None):
    """
    Arguments: 
        - key      : Google API key
        - longi    : longitude of the location to search around
        - lat      : latitude of the location to search around
        - radius   : distance in meters within which to return place results
        - keyword  : term (e.g. name, type, address) for place to search for 
        - minPrice : 0 ~ 4 for price range (0 being most affordable)
        - openNow  : return only places open now if true 
        - rankBy   : 'prominence' or 'distance'
        - placeType: type of place, see https://developers.google.com/places/web-service/supported_types

    Returns: 
        a list of parced places obtained 
    """
    locFormat = "%s,%s" % (lat, longi)
    params  = {"key": key, "location": locFormat, "radius": radius}

    if keyword != None:
        params["keyword"] = keyword
    if minPrice != None:
        params['minprice'] = minPrice
    if maxPrice != None:
        params['maxprice'] = maxPrice
    if openNow != None:
        params['opennow'] = openNow
    if rankBy != None:
        params['rankby'] = rankBy
    if placeType != None:
        params['type'] = placeType

    r = requests.get(url = PLACES_API, params = params)
    data = r.json()
    debug.writeJSON("database/json.txt", debug.pretty(data))

    return data["results"]

def getPlaces(data):
    """
    Arguments: 
        - data: a dictionary of JSON data sent from the user

    Returns: 
        - None
    """
    try:
        device_id = data["device_id"]
        code      = data["code"]
        longi     = float(data["lng"])
        lat       = float(data["lat"])
        radius    = float(data["radius"])
        placeType = data["category"]
        price     = int(data["price"])
        startTime = data["start_time"]
        duration  = float(data["duration"])
    except ValueError:
        raise PlacesError("Cannot parse numerical values")

    # Get the places user prefers near the user
    # apiCall(API_KEY, longi, lat, radius, placeType, price, price)
    return searchApiCall(API_KEY, longi, lat, radius, placeType)


if __name__ == "__main__":
    # apiCall(API_KEY, -117.842608, 33.649264, keyword="cafe")

    # temp = detailsApiCall(API_KEY, "ChIJ1SDxN9zY3IARfnQREgZsuvA", ["photos"])
    # print(temp)

    temp = distanceApiCall(API_KEY, -117.842608, 33.649264, -117.886332, 33.694895)
    print(temp)

