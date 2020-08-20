import pprint
import json


# ------ DEBUGGING FUNCTIONS -----
def pretty(data):
    return pprint.pformat(data)

def writeJSON(filePath, data):
    with open(filePath, "w") as f:
        json.dump(data, f)

def writeFile(filePath, string):
    with open(filePath, "w") as f:
        f.write(string)


