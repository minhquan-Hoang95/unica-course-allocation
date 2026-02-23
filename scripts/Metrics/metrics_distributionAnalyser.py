from metrics_utils import *
import matplotlib.pyplot as plt
from scipy import stats

#https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.goodness_of_fit.html
#https://en.wikipedia.org/wiki/Exponential_distribution
# H0: The data comes from the specified distribution
# H1: The data deviates from this distribution
def testDistributions(rankMatrix:np.ndarray) -> tuple[bool, float]:
    ...

if __name__ == "__main__":
    # Get datasets
    affectations, preferences, courses = getData(DEFAULT_AFFECTATIONS_PATH, DEFAULT_PREFERENCES_PATH, DEFAULT_COURSES_PATH)
    
    # Computer the rank matrix
    rankMatrix = computeRankMatrix(affectations, preferences)
    testDistributions(rankMatrix)