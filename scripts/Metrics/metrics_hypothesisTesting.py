from typing import Any

import metrics_utils as mu
import numpy as np
import pandas as pd
from metrics_aggregationMetrics import PARETO_FUNCTION
from scipy import stats


def areGroupDifferent(
    vectors: pd.DataFrame, metrics: list[PARETO_FUNCTION], groupCol: str | int = "track"
) -> dict[str, Any]:
    """Function to perform Kruskal-Wallis H test on independent samples and groups. First, we check whether the distributions of each group are equal for a given metric (if multiple metrics, then perform this test one time per metric).
    Then, performs pairwise Mann-Witney U test with (alternative = greater) to detect the diverging distributions.

    Args:
        vectors (pd.DataFrame): The dataframe containing the vectors we can compare for groups.
        metrics (list[PARETO_FUNCTION]): A list of metrics to test. The metrics must be available in the dataframe given above.
        groupCol (str | int, optional): If str, then treat then make the groups based on the unique values of this column. If int, then process the dataframe in order and create groups of the given size. Defaults to "track".

    Returns:
        dict[str,Any]: A dictionary containing the results and additional informations about the performed tests. `'groups'` contains the name of each processed groups in order, `'Kruskal'` and `'MannWhitneyU'` information about the tests,
        '`{metric}_Kruskal`' the p-value of the resulting Kruskal-Wallis test for the given metric. Finally, '`{metric}_MannWhitneyU`' contains a matrix of p-value in the form [[p(g1-g1), p(g2-g1),...],[p(g1-g2),p(g2,g2),...],...] where g1 corresponds
        to the first group of `'groups'`, g2 the second and so on. The alternative used (gx-gy) is gx stochastically greater than gy.
    """
    # Generate the groups
    groups = []
    groupsName = []

    # On the provided column if given
    if isinstance(groupCol, str):
        for group in vectors[groupCol].unique():
            # Register the metrics and the name of the group
            groups.append(vectors.loc[vectors[groupCol] == group, metrics].copy())
            groupsName.append(group)

    # Create the groups from scratch as the number of student in each group in student id order.
    elif isinstance(groupCol, int):
        # Get the length of the dataframe
        entitiyNumber = vectors.shape[0]

        # Create and register the groups
        for i in range(0, entitiyNumber, groupCol):
            groups.append(vectors.loc[i : i + groupCol, metrics].copy())
            groupsName.append(f"{i}..{min(i + groupCol, entitiyNumber)}")

    # Initialise results and add some interpretation informations
    results = {}
    results["groups"] = groupsName
    results["Kruskal"] = {
        "Desc.": "Kruskal-Wallis H test for independent samples and groups.",
        "H0": "All the groups have the same distribution.",
        "H1": "At least one group have different distribution",
    }
    results["MannWhitneyU"] = {
        "Desc.": "Mann-Whitney U test (Wilcoxon rank-sum test).",
        "H0": "The two groups have the same distribution.",
        "H1": "The distribution of group 1 is stochastically greater than the distribution of group 2, i.e. group 1 have generally higher values than group 2.",
        "Alt.": "greater",
    }

    # Generate the metrics
    for metric in metrics:
        # Retrieve the vectors of each group for the given metric
        testVectors = []
        for group in groups:
            testVectors.append(group[[metric]].to_numpy())

        # Compute the Kruskal test and retrieve the p-value for each metric
        results[f"{metric}_Kruskal"] = stats.kruskal(*testVectors).pvalue[0]

        # For each metric and group, compute the mann-whitney U test with the greater alternative and store the result in a numpy array.
        twoVStwoResults = np.zeros((len(groups), len(groups)))
        for i, vec1 in enumerate(testVectors):
            for j, vec2 in enumerate(testVectors):
                # Compute the p-value
                twoVStwoResults[i, j] = stats.mannwhitneyu(
                    vec1, vec2, alternative="greater"
                ).pvalue[0]
        # Store the result for each group comparisons.
        results[f"{metric}_MannWhitneyU"] = twoVStwoResults.tolist()

    # Return the results
    return results


if __name__ == "__main__":
    # Get datasets
    coursesVectors, studentsVectors = mu.getData(
        mu.DEFAULT_OUT_COURSES_VEC_PATH, mu.DEFAULT_OUT_STUDENTS_VEC_PATH
    )

    # See if students have different affectation wellfare between tracks
    areGroupDifferent(studentsVectors, ["sum", "mean", "median"], "track")

    # See if students have different affectation wellfare depending on when they answered the form
    areGroupDifferent(studentsVectors, ["sum", "mean", "median"], 10)

    # See if courses have different preferences distributions (does not have any sens since n is too low, but can be done for example.)
    areGroupDifferent(coursesVectors, ["lastRank"], 1)

    # See if students have different affectation over their choices of course number
    areGroupDifferent(studentsVectors, ["sum", "mean", "median"], "n")
