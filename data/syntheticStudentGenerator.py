# ==============================
# Student Preferences Generator
# ==============================
#
# This script generates random student course preferences
# compatible with the course allocation optimization model.
#
# Key properties:
# 1. Mid-rank/ Average Rank for ties
# 2. Mandatory courses ranked before optional courses
# 3. Rankings consistent across students
# 4. Output compatible with OPL input format


# Import the libraries
import numpy as np
from scipy.stats import rankdata
import pandas as pd
import json

# Define the outfile
OUTFILE = "studentsRandom.csv"

# About seed and preferences
SEED = None
RNG = np.random.RandomState(SEED)

# Define the frequency of each track
students:dict[str,int] = {
    "N":75,
    "AI":30,
    "CS":45
}

# Get the different lectures and their number
courses = pd.read_csv("coursesS1.csv")
M = courses.loc[:,"courseID"].max()

# Get the tracks minimum optional and maximum
with open("parameters.json", "r") as file:
    tracksData = json.load(file)["spe"]

# Predefine a random order over students
order = []
while students["N"] > 0:
    
    # Get a random track that is still possible
    possibleKeys = [k for k in students.keys() if students[k] > 0 and k != "N"]
    randomKey = RNG.choice(possibleKeys)
    
    # Keep it in the order and remove this possibility for the next choices
    order.append(randomKey)
    students["N"] -= 1
    students[randomKey] -=1

# Generate the CSV header of the random students
with open(OUTFILE, "w") as file:
    file.write("studentID," + ",".join([k + "_track" for k in students.keys() if k != "N"]) + ",maxOptional," + ",".join([f"Rg{i}" for i in range(1, M+1)]) + "\n")

# Generate the preferences and save them
for studentID, curriculum in enumerate(order, start=1):
    # Initialise to random rank
    rg = RNG.randint(M-1,size=M) + 2
    # Retrieve mandatory course for the selected track
    mandatoryCourses = courses[courses[curriculum + "_track"]==True].loc[:,"courseID"].to_numpy(dtype=int)    
    # Set mandatory courses
    rg[mandatoryCourses-1] = 1

    # Mid-rank normalization
    # Ensures mid-rank normalization property
    # Example :
    # raw values: 1,2,3,3
    # ranks:      1,2,3.5,3.5
    # Property:
    # Sum of ranks is constant:
    #
    #    sum = M(M+1)/2
    #
    # This guarantees consistency across students.

    ranks = rankdata(rg, method="average")
    
    # Get the authorised number of optional courses to choose from a particular track 
    minOptional = tracksData[curriculum+"_track"]["minNj"]
    maxOptional = tracksData[curriculum+"_track"]["maxNj"]
    optionalNumber = RNG.randint(minOptional, maxOptional+1)
    

    # Ensures mid-rank normalization property
    # np.isclose(a,b) checks if two numbers are almost equal ex : 10 == 10.00001 wich can happend with float 
    assert np.isclose(ranks.sum(),M * (M + 1) / 2), "Rank normalization failed"


    # Save the data
    with open(OUTFILE, "a") as file:
        # Put studentID
        file.write(f"{studentID},")
        # Put the one-hot encoded track selector 
        file.write(f"{','.join(map(str,[curriculum==k for k in students.keys() if k!='N'])).lower()},")
        # Put optional number of course selected
        file.write(f"{optionalNumber},")
        # Put the midpoint-normalised rank
        file.write(f"{','.join(map(str,ranks))}\n")