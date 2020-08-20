import random
import string



def generateRoomCode(length=5):
    """
    Arguments: 
        - length: the number of ascii characters to generate

    Returns: 
        a string of length 'length' with random chars. 
    """
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


if __name__ == "__main__":
    print(generateRoomCode())


