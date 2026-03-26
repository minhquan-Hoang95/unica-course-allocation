# Make aggregation like sum of sum rank, mean of sum rank, mean of last rank, etc.
import time
from collections.abc import Callable
from functools import partial
from typing import Literal

import metrics_utils as mu
import numpy as np
import pandas as pd
from scipy import stats

PARETO_FUNCTION = Literal[
    "sum",
    "mean",
    "var",
    "std",
    "median",
    "q1",
    "q3",
    "n",
    "firstRank",
    "lastRank",
    "minStudentRank",
    "maxStudentRank",
    "requested",
    "optionalCorrectedRankSum",
    "lastMandatoryOptionalRank",
    "rankedVSrequested",
    "maxRankDistance",
    "minRankDistance",
    "correctedMaxRankDistance",
    "optionalCorrectedQ1",
    "optionalCorrectedQ3",
    "optionalCorrectedMedian",
    "optionalCorrectedMean",
    "optionalCorrectedVar",
    "optionalCorrectedStd",
    "IQR",
    "optionalCorrectedIQR",
]

DEFAULT_OUT_COURSES_METRICS_PATH = "out/coursesMetrics.csv"
DEFAULT_OUT_STUDENTS_METRICS_PATH = "out/studentsMetrics.csv"


def getVectorsFromCSV(*paths: str) -> tuple[pd.DataFrame, ...]:
    return tuple([pd.read_csv(path) for path in paths])


def getBaseAggregationMetrics(
    vectors: pd.DataFrame,
    additional_fnc: dict[str, partial | Callable] | None = None,
    *post_aggregation_fnc: dict[str, partial | Callable],
) -> pd.DataFrame:
    """Function to aggregates the vectors metrics precedently computed using `mu.computeBaseVectors`. By default, the results includes the number of entity, the number of unique classes (for categorial data), the mode (for categorial data), the frequency of the mode (for categorial data),
    the mean, the std, the min, all the 5,10,15,...,85,90,95% quantiles, and the maximum.

    Args:
        vectors (pd.DataFrame): The vectors of metrics computed precedently.
        additional_fnc (Optional[dict[str, partial  |  Callable]], optional): Additional functions that aggregates data based on the vectors dataframe. Defaults to None.
        *post_df_fnc (tuple[dict[str,partial[np.ndarray]|Callable]]): Additional functions that use the aggregated dataframe to compute additional metrics. Useful for metametrics.

    Returns:
        pd.DataFrame: A dataframe containing all the metrics.
    """
    # Prepare external functions
    if additional_fnc is None:
        additional_fnc = {}
    if post_aggregation_fnc is None:
        post_aggregation_fnc = ()

    # Get everything except course and student id
    df = vectors.iloc[:, 1:].copy(deep=True)
    # Get first metrics
    described_df = df.describe(
        include="all", percentiles=[i / 100 for i in range(5, 100, 5)]
    )

    # Apply additional functions
    for key, value in additional_fnc.items():
        try:
            described_df.loc[key, :] = value(df)
        except TypeError:
            described_df.loc[key, described_df.dtypes != "object"] = value(
                df.loc[:, df.dtypes != "object"]
            )

    # Set up the post-processing function (aggregation operations over columns), in a list such that it is possible to chain multiple level of operations and intermediate ones
    post_fncs = [{}]

    # Add the different level of external post aggregation functions.
    for postAggregation in post_aggregation_fnc:
        post_fncs.append(postAggregation)

    # Apply functions
    for post in post_fncs:
        for key, value in post.items():
            described_df.loc[key, :] = value(described_df)

    return described_df


def getAdditionalAggregationFunctions() -> dict[str, Callable | partial]:
    """Additional aggregations functions for the `getBaseAggregationMetrics` function. It includes the ***skewness*** (measure of assymetry based on moments), the
    ***kurtosis*** (how flat is the distribution), and the gini coefficient (inequality measure).

    Returns:
        dict[str, Callable | partial]: A dictionary of function to feed in `getBaseAggregationMetrics`.
    """

    def giniCoefficient(df: pd.DataFrame):
        # Compute the gini coefficient for each columns: ∑∑|x_i-x_j|/(2n²E[x])
        def gini(col: pd.Series):
            s = 0
            for i in col:
                for j in col:
                    s += abs(i - j)
            return s / (2 * col.mean() * col.shape[0] ** 2)

        return df.apply(gini)

    return {
        "Skewness": partial(stats.skew, bias=True),
        "Kurtosis": partial(stats.kurtosis, bias=True),
        "GiniCoefficient": giniCoefficient,
    }


def getAdditionalAggregationPostFunctions() -> tuple[dict[str, Callable | partial]]:
    """Additional Post aggregation functions to feed in `getBaseAggregationMetrics`. It includes the ***IQR*** (Inter Quartile Range) and the
    ***Yule Assymetry*** (measure of assymetry based on quantile).

    Returns:
        tuple[dict[str, Callable | partial]]: A tuple containing the functions to feed.
    """

    return (
        {"IQR": lambda dataframe: dataframe.loc["75%", :] - dataframe.loc["25%", :]},
        {
            "Yule_assymetry": lambda dataframe: (
                (
                    dataframe.loc["25%", :]
                    + dataframe.loc["75%", :]
                    - 2 * dataframe.loc["50%", :]
                )
                / dataframe.loc["IQR", :]
            )
        },
    )


def getPossibleParetoExchanges(
    affectations: pd.DataFrame,
    preferences: pd.DataFrame,
    courses: pd.DataFrame,
    parameter: dict,
    paretoFunction: PARETO_FUNCTION = "optionalCorrectedRankSum",
    mode: Literal["min", "max"] = "min",
    returnTechnicalExchange: bool = False,
    verbose: bool = True,
) -> list[tuple[int, int]] | tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """A function that determine from the affectations and preferences of each student if some affectations could be swapped in order to improve a defined metric for both student (Pareto Exchange).
    It does also return the possibles exchanges if asked (Technical exchanges: A student cannot have more courses than it asked. It must have all the mandatory lectures of its track).

    Args:
        affectations (pd.DataFrame): The dataframe of affectation for each student.
        preferences (pd.DataFrame): The dataframe of preferences of each student.
        courses (pd.DataFrame): The dataframe containing the informations over each courses.
        parameter (dict): Parameter of the system. A dict including the number of courses, students and the specificities of each track.
        paretoFunction (PARETO_FUNCTION, optional): A metrics which is used in `mu.computeBaseVectors` or available through `mu` additional functions/post-functions for students. Defaults to "optionalCorrectedRankSum".
        mode (Literal[&quot;min&quot;,&quot;max&quot;], optional): If the swap must minimise or maximise the metric. Defaults to "min".
        returnTechnicalExchange (bool, optional): Return exchanges that are not Technical exchanges without necessarily being Pareto exchange. Defaults to False.
        verbose (bool, optional): Do the user want to be informed about the function running time. Defaults to True.

    Returns:
        list[tuple[int, int]] | tuple[list[tuple[int,int]],list[tuple[int,int]]]: A list containing the possible exchanges. If ***returnTechnicalExchange*** is True then return a tuple with the list of Pareto exchanges in first position and a list of technical exchange in second position. Note that Pareto exchanges are included into technical exchanges.
    """

    # Initialise the timer for the print
    if verbose:
        begin = time.time()

    # Initialise the lists that will return the possibles couples.
    if returnTechnicalExchange:
        technicalExchange = []
    paretoExchange = []

    # Transform the affectations into a matrix
    affectationsMatrix = affectations.loc[
        :, affectations.columns.str.startswith("c")
    ].to_numpy()

    # Transforms the preferences into a matrix
    preferencesMatrix = preferences.loc[
        :, preferences.columns.str.startswith("Rg")
    ].to_numpy()

    # Get the maximal number of courses a student a want to participate
    coursesRequestVector = preferences.loc[:, "maxOptional"].to_numpy()

    # Get the mandatory lectures
    mandatoryLectures = mu.getStudentsMandatoryLecturesFromTrack(
        courses, mu.getStudentsTrackFromPreferences(preferences)
    )
    mandatoryLecturesIndices = []
    # Get the indices of each mandatory lectures
    for lectures in mandatoryLectures:
        if lectures == []:
            # If false, then no one is selected within a numpy array slice
            mandatoryLecturesIndices.append(False)
        else:
            mandatoryLecturesIndices.append(
                list(map(lambda x: int(str.removeprefix(x, "Rg")) - 1, lectures))
            )

    # For each student, look if it is possible to exchange
    for student1 in preferences.loc[:, "studentID"]:
        # Compute the partial rank matrix of student 1
        startStudent1RankMatrix = (
            affectationsMatrix[student1 - 1, :] * preferencesMatrix[student1 - 1, :]
        )

        # For each student having a student id over the one of student 2
        for student2 in preferences.loc[
            preferences["studentID"] > student1, "studentID"
        ]:
            # Check if student 1 can exchange with student 2 affectation regarding to student 1 mandatory lectures
            canStudent1ExchangeWithStudent2 = np.array_equal(
                affectationsMatrix[
                    student1 - 1, mandatoryLecturesIndices[student1 - 1]
                ],
                affectationsMatrix[
                    student2 - 1, mandatoryLecturesIndices[student1 - 1]
                ],
            )
            if not canStudent1ExchangeWithStudent2:
                continue

            # Check if student 2 can exchange with student 1 affectation regarding to student 2 mandatory lectures
            canStudent2ExchangeWithStudent1 = np.array_equal(
                affectationsMatrix[
                    student1 - 1, mandatoryLecturesIndices[student2 - 1]
                ],
                affectationsMatrix[
                    student2 - 1, mandatoryLecturesIndices[student2 - 1]
                ],
            )
            if not canStudent2ExchangeWithStudent1:
                continue

            # Does student 1 have more courses than student 2 whishes?
            haveStudent1LessWhishesThanStudent2 = (
                affectationsMatrix[student1 - 1, :].sum()
                <= coursesRequestVector[student2 - 1]
            )
            if not haveStudent1LessWhishesThanStudent2:
                continue

            # Does student 2 have more courses than student 1 whishes
            haveStudent2LessWhishesThanStudent1 = (
                affectationsMatrix[student2 - 1, :].sum()
                <= coursesRequestVector[student1 - 1]
            )
            if not haveStudent2LessWhishesThanStudent1:
                continue

            # At this point, the exchange is technically possible. So we register it if we also want non-necesseraly Pareto exchanges.
            if returnTechnicalExchange:
                technicalExchange.append((student1, student2))

            # Form the partial rank matrix of student 1 and student 2 before swapping affectations
            startingRankMatrix = np.array(
                [
                    startStudent1RankMatrix,
                    affectationsMatrix[student2 - 1, :]
                    * preferencesMatrix[student2 - 1, :],
                ]
            )

            # Same, but after swapping the affectations
            swapRankMatrix = np.array(
                [
                    affectationsMatrix[student2 - 1, :]
                    * preferencesMatrix[student1 - 1, :],
                    affectationsMatrix[student1 - 1, :]
                    * preferencesMatrix[student2 - 1, :],
                ]
            )

            # Filter to get the right metrics (we do not want metrics that keeps other students in memory)
            studentPreferencesFilter = np.logical_or(
                preferences["studentID"] == student1,
                preferences["studentID"] == student2,
            )

            # Get additional function for getBaseMetrics (This part could be improved with a dictionary to get if the exchange is Pareto under each metrics instead of one)
            additionalFunc = mu.getAdditionalCoursesBasedOnStudentsFunction(
                preferences.loc[studentPreferencesFilter, :], courses, parameter
            )
            additionalFunc |= mu.getAdditionalPreferencesBasedOnStudentsFunction(
                preferences.loc[studentPreferencesFilter, :]
            )

            # Get additional postfunction
            postFunc = mu.getAdditionalPostOnStudentsFunction()

            # Get all the metrics before applying the swap
            startVectors = mu.computeBaseVectors(
                startingRankMatrix, additionalFunc, *postFunc, onStudent=True
            )

            # Get all the metrics after applying the swap
            swapVectors = mu.computeBaseVectors(
                swapRankMatrix, additionalFunc, *postFunc, onStudent=True
            )

            # If the swap resulted in better metrics according to the mode, and this for all parties or at least one, register the swap as Pareto Exchange
            if (
                mode == "min"
                and np.all(
                    startVectors.loc[:, paretoFunction]
                    >= swapVectors.loc[:, paretoFunction]
                )
                or mode == "max"
                and np.all(
                    startVectors.loc[:, paretoFunction]
                    <= swapVectors.loc[:, paretoFunction]
                )
            ):
                paretoExchange.append((student1, student2))
                if verbose:
                    print(
                        f"{student1} and {student2} are Pareto exchangeable under {paretoFunction} [{mode}]"
                    )

            # Inform the user on the function running time
            elif verbose and student1 % 5 == 0 and student2 == student1 + 1:
                print(
                    f"[{time.time() - begin:.5f}s] Student couple ({student1, student2})."
                )

    # Return the Pareto exchanges, but also possible exchanges in general if asked.
    if returnTechnicalExchange:
        return paretoExchange, technicalExchange
    return paretoExchange


if __name__ == "__main__":
    # Get the vectors
    coursesVectors, studentsVectors = getVectorsFromCSV(
        mu.DEFAULT_OUT_COURSES_VEC_PATH, mu.DEFAULT_OUT_STUDENTS_VEC_PATH
    )

    # Get all the other files
    affectations, preferences, courses = mu.getData(
        mu.DEFAULT_IN_AFFECTATIONS_PATH,
        mu.DEFAULT_IN_PREFERENCES_PATH,
        mu.DEFAULT_IN_COURSES_PATH,
    )
    parameters = mu.getParameters(mu.DEFAULT_IN_PARAMETERS_PATH)

    # Get the Pareto and possible exchanges
    paretoExchanges, technicalExchanges = getPossibleParetoExchanges(
        affectations,
        preferences,
        courses,
        parameters,
        "lastMandatoryOptionalRank",
        "min",
        returnTechnicalExchange=True,
    )
    print(
        f"There is {len(paretoExchanges)} Pareto exchanges possible over {len(technicalExchanges)} possible exchanges. The Pareto exchange density is {len(paretoExchanges) / len(technicalExchanges):.3f}"
    )

    # Get the additional functions
    additional_fncs = getAdditionalAggregationFunctions()
    additional_post_fncs = getAdditionalAggregationPostFunctions()

    # Computes Metrics for courses
    getBaseAggregationMetrics(
        coursesVectors, additional_fncs, *additional_post_fncs
    ).to_csv(DEFAULT_OUT_COURSES_METRICS_PATH)

    # Compute metrics for students
    getBaseAggregationMetrics(
        studentsVectors, additional_fncs, *additional_post_fncs
    ).to_csv(DEFAULT_OUT_STUDENTS_METRICS_PATH)
