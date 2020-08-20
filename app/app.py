import places
import room
import db_control

from flask import Flask, abort, jsonify, render_template, request
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def hello():
    """
    Home screen, nothing here
    """
    return "hello angelo and ryan and rebekah and nate\n"

@app.route("/setprefs", methods=['POST'])
def setPrefs():
    """
    User send information on their preferences, and location through 
    this POST request. Server obtains a list of places around the user
    based on their prefs.
    """
    if request.method == "POST":
        # parse JSON data
        req_data = request.get_json(force=True)

        # put the parsed JSON data into our db
        db = db_control.connectDB()
        db_control.updatePreferences(db, **req_data)
        db_control.closeDB(db)

        # obtain places list, not returned because it's stored in db
        try:
            googleResults = places.getPlaces(req_data)
            open_hours    = places.getHours(googleResults)

            # merge with the places db and update scores for each place
            db = db_control.connectDB()
            db_control.updateScores(db, googleResults, open_hours, **req_data)

            # list of places, inside list are tuples (i.e. (place_id, total_votes))
            placesList = db_control.getScores(db, req_data["code"])

            date = db_control.date_intersect(db, req_data["code"])

            if len(date) != 0:
                suggestedRange = date[0]

                for r in date[1:]:
                    if suggestedRange.is_intersection(r):
                        suggestedRange = suggestedRange.intersection(r)
                    else:
                        break

                suggestedRange.start_time_format = "%H:%M"
                suggestedRange = suggestedRange.get_start_time_str()
            else:
                suggestedRange = "NA"

            db_control.closeDB(db)
            placesInfo = places.getPlacesDetails(placesList, **req_data)
            placesInfo.update({"suggested_time": suggestedRange})

            return jsonify(placesInfo)

        except places.PlacesError as e:
            abort(500, str(e))
    else:
        abort(401)

@app.route("/generate", methods=["GET"])
def generate():
    """
    Generate a room code and return it to the user
    """
    #req_data = request.get_json(force=True) 
    #did = req_data["device_id"]

    roomCode = room.generateRoomCode()

    # insert did & roomcode into db
    #db = db_control.connectDB()
    #db_control.insertCode(db, did, roomCode)
    #db_control.closeDB(db)

    return jsonify(code=roomCode)

@app.route("/existing", methods=["POST"])
def existing():
    req_data = request.get_json(force=True)
    did = req_data["device_id"]
    code = req_data["code"]

    db = db_control.connectDB()
    db_control.insertCode(db, did, code)
    db_control.closeDB(db)

    return jsonify(code=code)

@app.route("/getprefs", methods=["POST"])
def getPrefs():
    """
    Get the user's previous preferences from the database. If the user
    does not exist in the db, return nulls.
    """
    # parse JSON 
    req_data = request.get_json(force=True)
    did  = req_data["device_id"]
    code = req_data["code"]

    # Get user's previous preferences from db 
    try:
        db    = db_control.connectDB()
        prefs = db_control.selectPreferences(db, did, code)
        db_control.closeDB(db)
    except db_control.NoUsersError as e:
        abort(500, str(e))

    return jsonify(prefs)

@app.route("/vote", methods=["POST"])
def vote():
    """
    Gets the room code, the did, and the place_id, then increment 
    the # of votes in our db.
    """
    req_data = request.get_json(force=True)
    did      = req_data["device_id"]
    code     = req_data["code"]
    place_id = req_data["place_id"]

    db = db_control.connectDB()
    db_control.updateVotes(db, did, code, place_id)

    # update the user's list of places with the newest ranking
    placesList = db_control.getScores(db)

    db_control.closeDB(db)
    placesInfo = places.getPlacesDetails(placesList)
    return jsonify(placesInfo)



if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')

