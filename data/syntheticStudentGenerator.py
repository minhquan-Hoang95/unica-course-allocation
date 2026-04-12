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
#
# Usage:
#   python syntheticStudentGenerator.py [--n 75] [--ai 30] [--cs 45] [--seed 42]
#   python syntheticStudentGenerator.py --n 100 --ai 40 --cs 60 --seed 0
#   python3 syntheticStudentGenerator.py --n 110 --ai 40 --cs 70 --seed 42 --dat students.dat

import argparse
import numpy as np
from scipy.stats import rankdata
import pandas as pd
import json
from convertisseur import read_courses, compute_mmax, read_params, write_dat


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic student course preferences.")
    parser.add_argument("--n",       type=int, default=75,                   help="Total number of students")
    parser.add_argument("--ai",      type=int, default=30,                   help="Number of AI track students")
    parser.add_argument("--cs",      type=int, default=45,                   help="Number of CS track students")
    parser.add_argument("--seed",    type=int, default=None,                 help="Random seed (default: None = non-reproducible)")
    parser.add_argument("--courses", type=str, default="coursesS1.csv",      help="Path to courses CSV")
    parser.add_argument("--params",  type=str, default="parameters.json",    help="Path to parameters JSON")
    parser.add_argument("--out",     type=str, default="studentsRandom.csv", help="Output CSV file")
    parser.add_argument("--dat",     type=str, default=None,                 help="If set, also generate a .dat file at this path")
    args = parser.parse_args()

    if args.ai + args.cs != args.n:
        parser.error(f"--ai ({args.ai}) + --cs ({args.cs}) must equal --n ({args.n})")

    return args


def generate_order(students, RNG):
    # Predefine a random order over students
    order = []
    while students["N"] > 0:
        # Get a random track that is still possible
        possibleKeys = [k for k in students.keys() if students[k] > 0 and k != "N"]
        randomKey = RNG.choice(possibleKeys)
        # Keep it in the order and remove this possibility for the next choices
        order.append(randomKey)
        students["N"] -= 1
        students[randomKey] -= 1
    return order


def write_header(OUTFILE, students, M):
    with open(OUTFILE, "w") as file:
        file.write("studentID," + ",".join([k + "_track" for k in students.keys() if k != "N"]) + ",maxOptional," + ",".join([f"Rg{i}" for i in range(1, M+1)]) + "\n")


def generate_student_ranks(curriculum, courses, M, tracksData, RNG):
    # Initialise to random rank
    rg = RNG.randint(M-1, size=M) + 2

    # Retrieve mandatory course for the selected track
    mandatoryCourses = courses[courses[curriculum + "_track"] == True].loc[:, "courseID"].to_numpy(dtype=int)

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
    # np.isclose(a,b) checks if two numbers are almost equal ex : 10 == 10.00001 which can happen with float
    assert np.isclose(ranks.sum(), M * (M + 1) / 2), "Rank normalization failed"

    return ranks, optionalNumber


def write_student(OUTFILE, studentID, curriculum, students, optionalNumber, ranks):
    with open(OUTFILE, "a") as file:
        # Put studentID
        file.write(f"{studentID},")
        # Put the one-hot encoded track selector
        file.write(f"{','.join(map(str, [curriculum==k for k in students.keys() if k!='N'])).lower()},")
        # Put optional number of course selected
        file.write(f"{optionalNumber},")
        # Put the midpoint-normalised rank
        file.write(f"{','.join(map(str, ranks))}\n")


def generate_preferences(OUTFILE, order, students, courses, M, tracksData, RNG):
    # Generate the preferences and save them
    parc = []
    maxOptional = []
    r = []

    for studentID, curriculum in enumerate(order, start=1):
        ranks, optionalNumber = generate_student_ranks(curriculum, courses, M, tracksData, RNG)
        write_student(OUTFILE, studentID, curriculum, students, optionalNumber, ranks)

        # Collect data in memory for direct .dat conversion (avoids re-reading the CSV)
        parc.append(1 if curriculum == "CS" else 2)
        maxOptional.append(optionalNumber)
        r.append(list(ranks))

    return parc, maxOptional, r


def main():
    args = parse_args()

    OUTFILE = args.out
    RNG = np.random.RandomState(args.seed)

    students: dict[str, int] = {
        "N":  args.n,
        "AI": args.ai,
        "CS": args.cs
    }

    courses = pd.read_csv(args.courses)
    M = courses.loc[:, "courseID"].max()

    with open(args.params, "r") as file:
        tracksData = json.load(file)["spe"]

    order = generate_order(students, RNG)
    write_header(OUTFILE, students, M)
    parc, maxOptional, r = generate_preferences(OUTFILE, order, students, courses, M, tracksData, RNG)

    print(f"Generated {args.n} students ({args.ai} AI, {args.cs} CS) -> {OUTFILE}")

    # Direct .dat conversion without re-reading the CSV
    if args.dat:
        n = args.n
        p = 2
        c, conflicts, mandatory, mandCS, mandIA = read_courses(args.courses, n)
        mmax = compute_mmax(parc, maxOptional, mandCS, mandIA)
        mmin, gmin, gmax, objType = read_params(args.params)
        write_dat(args.dat, n, M, p, gmin, gmax, objType, c, conflicts, mmin, mandatory, mmax, parc, r)
        print(f"Fichier .dat généré : {args.dat}")


if __name__ == "__main__":
    main()