from datetime import datetime
from datetime import timedelta
from datetimerange import DateTimeRange
import MySQLdb



class NoUsersError(Exception):
    pass


def connectDB():
    """
    Connects to a db on the server, returns a reference to it
    """
    db = MySQLdb.connect(host="w2m.camj7lel0wu4.us-west-1.rds.amazonaws.com",
                         user="admin", passwd="hackuci2020", db="w2m_db")

    return db

def closeDB(db):
    """
    Close the connection to db database. 
    """
    db.close()

def insertCode(db, did, code):
    """ 
    Insert a new user (i.e. did) to a room (i.e. code). 
    """
    cur = db.cursor()

    try:
        cur.execute("INSERT INTO users VALUES (%s,%s,null,null,null,null,null,null,null);", (did, code))
        db.commit()

        cur.close()
    except:
        db.rollback()

def updatePreferences(db, **kwargs):
    """
    Update the existing entry preferences to the new one. 
    There will be no case where the (did, code) is not in
    the db, since we get the (did, code) in login screen
    and put nulls in the rest of the columns.
    Arguments: 
        - db    : database storing the info 
        - kwargs: keyword arguments for device_id, code, longitude, latitude... etc.
    Returns: 
        - None
    """
    cur = db.cursor()

    updateQ = "UPDATE users SET "

    prefString = ""
    for key, item in kwargs.items():
        if key != "device_id" and key != "code":
            prefString += "{} = '{}',".format(key, item)

    updateQ += prefString[:-1]
    updateQ += " WHERE device_id = '{}' AND code = '{}'".format(kwargs["device_id"], kwargs["code"])

    cur.execute(updateQ)
    db.commit()

    cur.close()

def selectPreferences(db, did, code):
    """ 
    Extract a user's (i.e. did) past preferences in a room (i.e. code)
    """
    cur = db.cursor()

    # get column names
    cur.execute("DESCRIBE users")
    columnNames = (entry[0] for entry in cur.fetchall()[2:])

    cur.execute("SELECT lat, lng, radius, category, price, start_time, duration FROM users WHERE device_id = %s AND code = %s", (did, code))
    row = cur.fetchall()

    if len(row) == 1:
        dictInit = tuple(zip(columnNames, row[0]))
        result = dict(dictInit)
    else:
        # if there are no users in the db
        raise NoUsersError("Database should have returned a user preference")

    cur.close()
    return result

def updateScores(db, places_info, open_hours, **kwargs):
    """
    Takes in a list of places and their info. If the place is in the database, 
    update the database score. Otherwise, create a new row matching the user's 
    preferences (passed in from kwargs). 
    
    Arguments:
        - places_info: [{lat: -13, lng: -114...}, {...}, ...]
        - open_hours: {place_id: {open: "0800", "close": "2300"}}
        - kwargs: {lat: -14, lng: -551, ... }
    """
    did = kwargs["device_id"]
    # Get the room code
    code = kwargs["code"]

    # Get user's preferred times
    pref_start    = kwargs["start_time"].split(" ")[1]
    pref_start_dt = datetime.strptime(pref_start, "%H:%M:%S")
    duration      = int(kwargs["duration"])
    pref_end_dt   = pref_start_dt + timedelta(minutes=duration)

    # Get user's preferred price
    pref_price = kwargs["price"]

    # Get user's preferred category
    pref_category = kwargs["category"]
    if pref_category == "Activity":
        pref_category = {"park", "movie_theatre", "tourist_attraction", "museum", "stadium", "ammusement_park", "aquarium", "art_gallery", "bar"}
    elif pref_category == "Eating":
        pref_category = {"bar", "restaurant", "cafe", "shopping_mall"}
    elif pref_category == "Study":
        pref_category = {"library", "university", "cafe", "school", "book_store"}

    cur = db.cursor()

    # delete previous votes
    cur.execute("DELETE FROM votes WHERE device_id = %s AND code = %s", (did, code))
    db.commit()

    for place in places_info:
        place_id = place["place_id"]

        # match opening hours
        if open_hours[place_id] != "NA":
            place_open = open_hours[place_id]["open"]
            place_open = place_open[:2] + ":" + place_open[2:]

            place_close = open_hours[place_id]["close"]
            place_close = place_close[:2] + ":" + place_close[2:]

            place_open_dt = datetime.strptime(place_open, "%H:%M")
            place_close_dt = datetime.strptime(place_close, "%H:%M")

            if place_open_dt <= pref_start_dt and place_close_dt >= pref_end_dt:
                # increment the place's score in our db
                cur.execute("INSERT INTO votes VALUES (%s,%s,%s,0,%s,0,0) ON DUPLICATE KEY UPDATE price=price+0, time=time+1, category=category+0, votes=votes+0;",
                        (did, code, place_id, 1))
                db.commit()

        # match price range
        if "price_level" not in place:
            place_price = "0"
        else:
            place_price = str(place["price_level"])

        if place_price == "0":
            place_price = "1"
        elif place_price == "4":
            place_price = "3"

        if place_price == pref_price:
            cur.execute("INSERT INTO votes VALUES (%s,%s,%s,%s,0,0,0) ON DUPLICATE KEY UPDATE price=price+1, time=time+0, category=category+0, votes=votes+0;",
                    (did, code, place_id, 1))
            db.commit()
        # match category
        if "types" in place:
            place_categories = set(place["types"])
            if len(pref_category.intersection(place_categories)) != 0:
                cur.execute("INSERT INTO votes VALUES (%s,%s,%s,0,0,%s,0) ON DUPLICATE KEY UPDATE price=price+0, time=time+0, category=category+1, votes=votes+0;",
                        (did, code, place_id, 1))
                db.commit()


    cur.close()

def getScores(db, code):
    """
    Returns a list of 3-tuples (i.e. places_id, score, votes)
    """
    cur = db.cursor()

    cur.execute("SELECT place,SUM(price) + SUM(time) + SUM(category) as total, SUM(votes) AS trump FROM votes WHERE code=%s GROUP BY place ORDER BY SUM(votes) DESC, total DESC", [code])
    rows = cur.fetchall()

    cur.close()
    return rows

def updateVotes(db, did, code, place_id):
    """ 
    Increments the votes section in db based on user did, code, and place_id.
    """
    cur = db.cursor()

    cur.execute("update votes set votes = 0 where votes = 1 and device_id = %s and code = %s", (did, code))
    cur.execute("update votes set votes = 1 where device_id = %s and code = %s and place = %s", (did, code, place_id))
    db.commit()

    cur.close()

def date_intersect(db, code):
    """
    Gets all users in a room and finds the best intersected time frame to meet.
    """
    cur = db.cursor()

    cur.execute("SELECT start_time, duration FROM users WHERE code=%s;", [code])
    records = cur.fetchall()

    time_prefs = list()
    for r in records:
        if r[0] != None and r[1] != None:
            start_prefs = datetime.strptime(r[0],'%Y-%m-%d %H:%M:%S')
            end_prefs = start_prefs + timedelta(minutes=int(r[1]))
            time_range = DateTimeRange(start_prefs, end_prefs)
            time_prefs.append(time_range)

    time_prefs.sort(key = (lambda x : x.get_timedelta_second()), reverse=True)

    cur.close()

    return time_prefs

if __name__ == "__main__":
    db = connectDB()
    # insertCode(db, "123", "aoeig")

    # result = selectPreferences(db,  "169.234.76.142", "kdzjs")
    # print(result)

    updatePreferences(db, device_id="169.234.76.142", code="kdzjs", lat = "1", lng = "1", radius = "1", category = "1", price = "1", start_time = "1", duration = "1")

    closeDB(db)

                      
