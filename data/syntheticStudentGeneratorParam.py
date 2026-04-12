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
#   python syntheticStudentGenerator.py --n 100 --ai 40 --cs 60 --seed 0 --dat students.dat
#
# Demand profiles (--profile):
#   uniform    : all optional courses equally likely to be preferred (default)
#   hotspot    : a few courses are heavily preferred by most students
#   bottleneck : one single course attracts everyone -> capacity crisis
#   custom     : user-defined weights via --weights (one per course, comma-separated)
#
# Example extreme cases:
#   --profile bottleneck               # everyone wants course 1
#   --profile hotspot                  # courses 1-3 are very popular
#   --profile custom --weights 10,1,1,5,1,2   # manual weights per course

import argparse
import json

import numpy as np
import pandas as pd
from convertisseur import compute_mmax, read_courses, read_params, write_dat
from scipy.stats import rankdata

# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

# A profile maps a number of courses M to a weight vector of length M.
# Higher weight = course more likely to receive a good (low) rank.
# Mandatory courses ignore weights (they are always set to rank 1).


def build_profile(profile, M, weights_arg=None):
    if profile == "custom":
        if weights_arg is None:
            raise ValueError("--weights required for custom profile")
        weights = np.array([float(w) for w in weights_arg.split(",")])
        if len(weights) != M:
            raise ValueError(f"Expected {M} weights, got {len(weights)}")
        if (weights < 0).any():
            raise ValueError("Weights must be non-negative")

    else:
        weights = np.ones(M)

        if profile == "hotspot":
            weights[: max(1, M // 3)] *= 10

        elif profile == "bottleneck":
            weights[0] = 100

        elif profile != "uniform":
            raise ValueError(f"Unknown profile: {profile}")

    return weights / weights.sum()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic student course preferences."
    )
    parser.add_argument("--n", type=int, default=75, help="Total number of students")
    parser.add_argument(
        "--ai", type=int, default=30, help="Number of AI track students"
    )
    parser.add_argument(
        "--cs", type=int, default=45, help="Number of CS track students"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed (default: None = non-reproducible)",
    )
    parser.add_argument(
        "--courses", type=str, default="coursesS1.csv", help="Path to courses CSV"
    )
    parser.add_argument(
        "--params", type=str, default="parameters.json", help="Path to parameters JSON"
    )
    parser.add_argument(
        "--out", type=str, default="studentsRandom.csv", help="Output CSV file"
    )
    parser.add_argument(
        "--dat",
        type=str,
        default=None,
        help="If set, also generate a .dat file at this path",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="uniform",
        choices=["uniform", "hotspot", "bottleneck", "custom"],
        help="Demand profile: uniform (default), hotspot, bottleneck, custom",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Comma-separated weights per course, only with --profile custom. "
        "Example: --weights 10,1,1,5,1,2",
    )
    args = parser.parse_args()

    if args.ai + args.cs != args.n:
        parser.error(f"--ai ({args.ai}) + --cs ({args.cs}) must equal --n ({args.n})")

    return args


# ---------------------------------------------------------------------------
# Student order
# ---------------------------------------------------------------------------


def generate_order(students, RNG):
    # Predefine a random order over students
    order = []
    while students["N"] > 0:
        # Get a random track that is still possible
        possibleKeys = [k for k in students if students[k] > 0 and k != "N"]
        randomKey = RNG.choice(possibleKeys)
        # Keep it in the order and remove this possibility for the next choices
        order.append(randomKey)
        students["N"] -= 1
        students[randomKey] -= 1
    return order


# ---------------------------------------------------------------------------
# CSV header
# ---------------------------------------------------------------------------


def write_header(OUTFILE, students, M):
    with open(OUTFILE, "w") as file:
        file.write(
            "studentID,"
            + ",".join([k + "_track" for k in students if k != "N"])
            + ",maxOptional,"
            + ",".join([f"Rg{i}" for i in range(1, M + 1)])
            + "\n"
        )


# ---------------------------------------------------------------------------
# Rank generation
# ---------------------------------------------------------------------------


def generate_student_ranks(curriculum, courses, M, tracksData, RNG, probs):
    # Retrieve mandatory courses for the selected track
    mandatoryCourses = (
        courses[courses[curriculum + "_track"]].loc[:, "courseID"].to_numpy(dtype=int)
    )

    # Build optional course indices (0-based)
    optionalIdx = np.array([i for i in range(M) if (i + 1) not in mandatoryCourses])

    # Initialise to random rank in [2, M]
    rg = RNG.randint(M - 1, size=M) + 2

    # Set mandatory courses
    rg[mandatoryCourses - 1] = 1

    if len(optionalIdx) > 0:
        # Renormaliser les probabilités sur les cours optionnels
        optionalProbs = probs[optionalIdx]
        optionalProbs = optionalProbs / optionalProbs.sum()

        # Tirage aléatoire pondéré d’un ordre de préférence
        ordered = RNG.choice(
            optionalIdx, size=len(optionalIdx), replace=False, p=optionalProbs
        )

        # Assigner les rangs (2, 3, ..., M)
        for rank, course_idx in enumerate(ordered, start=2):
            rg[course_idx] = rank

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
    minOptional = tracksData[curriculum + "_track"]["minNj"]
    maxOptional = tracksData[curriculum + "_track"]["maxNj"]
    optionalNumber = RNG.randint(minOptional, maxOptional + 1)

    # Ensures mid-rank normalization property
    # np.isclose(a,b) checks if two numbers are almost equal ex : 10 == 10.00001 which can happen with float
    assert np.isclose(ranks.sum(), M * (M + 1) / 2), "Rank normalization failed"

    return ranks, optionalNumber


# ---------------------------------------------------------------------------
# CSV writing
# ---------------------------------------------------------------------------


def write_student(OUTFILE, studentID, curriculum, students, optionalNumber, ranks):
    with open(OUTFILE, "a") as file:
        # Put studentID
        file.write(f"{studentID},")
        # Put the one-hot encoded track selector
        file.write(
            f"{','.join(map(str, [curriculum == k for k in students if k != 'N'])).lower()},"
        )
        # Put optional number of course selected
        file.write(f"{optionalNumber},")
        # Put the midpoint-normalised rank
        file.write(f"{','.join(map(str, ranks))}\n")


def generate_preferences(OUTFILE, order, students, courses, M, tracksData, RNG, probs):
    # Generate the preferences and save them
    parc = []
    maxOptional = []
    r = []

    for studentID, curriculum in enumerate(order, start=1):
        ranks, optionalNumber = generate_student_ranks(
            curriculum, courses, M, tracksData, RNG, probs
        )
        write_student(OUTFILE, studentID, curriculum, students, optionalNumber, ranks)

        # Collect data in memory for direct .dat conversion (avoids re-reading the CSV)
        parc.append(1 if curriculum == "CS" else 2)
        maxOptional.append(optionalNumber)
        r.append(list(ranks))

    return parc, maxOptional, r


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    OUTFILE = args.out
    RNG = np.random.RandomState(args.seed)

    students: dict[str, int] = {"N": args.n, "AI": args.ai, "CS": args.cs}

    courses = pd.read_csv(args.courses)
    M = courses.loc[:, "courseID"].max()

    with open(args.params) as file:
        tracksData = json.load(file)["spe"]

    probs = build_profile(args.profile, M, args.weights)

    order = generate_order(students, RNG)
    write_header(OUTFILE, students, M)
    parc, maxOptional, r = generate_preferences(
        OUTFILE, order, students, courses, M, tracksData, RNG, probs
    )

    print(
        f"Generated {args.n} students ({args.ai} AI, {args.cs} CS) -> {OUTFILE}  [profile={args.profile}]"
    )

    # Direct .dat conversion without re-reading the CSV
    if args.dat:
        n = args.n
        p = 2
        c, conflicts, mandatory, mandCS, mandIA = read_courses(args.courses, n)
        mmax = compute_mmax(parc, maxOptional, mandCS, mandIA)
        mmin, gmin, gmax, objType = read_params(args.params)
        write_dat(
            args.dat,
            n,
            M,
            p,
            gmin,
            gmax,
            objType,
            c,
            conflicts,
            mmin,
            mandatory,
            mmax,
            parc,
            r,
        )
        print(f"Fichier .dat généré : {args.dat}")


if __name__ == "__main__":
    main()
