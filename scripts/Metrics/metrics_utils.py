import pandas as pd
import numpy as np
from typing import Optional, Callable
from functools import partial

DEFAULT_AFFECTATIONS_PATH = "srcFiles/FCFSaffectation.csv"
DEFAULT_PREFERENCES_PATH = "srcFiles/studentsRandom.csv"
DEFAULT_COURSES_PATH = "srcFiles/courses.csv"



def getData(*paths:str) -> tuple[pd.DataFrame, ...]:
    return tuple([pd.read_csv(path) for path in paths])

def computeRankMatrix(affectations:pd.DataFrame, preferences:pd.DataFrame) -> np.ndarray:
    # Crop to the necessary information
    affectationsMatrix = affectations.loc[:,affectations.columns.str.startswith("c")].to_numpy()
    preferencesMatrix = preferences.loc[:,preferences.columns.str.startswith("Rg")].to_numpy()
    
    # Return the matrix of selected ranked preferences
    return affectationsMatrix*preferencesMatrix

def computeBaseMetrics(rankMatrix:np.ndarray,
                       additional_fnc:Optional[dict[str, partial | Callable]] = None,
                       *post_aggregation_fnc:dict[str, partial | Callable],
                       onStudent:bool = True
                       ) -> pd.DataFrame:
    """Function that compute the basic statistics values on the ranks. This include the sum, mean, var, std, median, quartiles, n, the first and last rank granted.
    It is possible to include others functions.
    
    **Warning: You can provide external functions, but there is no warranty they will work properly.**

    Args:
        rankMatrix (np.ndarray): The matrix of rank
        onStudent (bool): If True compute the statistics on the student, otherwise on the lectures. Defaults to True
        additional_fnc (Optional[dict[str,partial[np.ndarray] | Callable]], optional): External functions acting on the rank matrix. Defaults to None.
        *post_aggregation_fnc (tuple[dict[str,partial[np.ndarray]|Callable]]): External functions acting on the dataframe, after the first metrics were computed. Useful for metametrics.

    Returns:
        pd.DataFrame: A dataframe formed by a column for each function and a row for each student.
    """
    
    # Prepare external functions
    if additional_fnc is None:
        additional_fnc = {}
    if post_aggregation_fnc is None:
        post_aggregation_fnc = ()
    # Prepare matrix
    if not onStudent:
        rankMatrix = rankMatrix.T
        
    # Base functions that are going to be calculated
    fncs = {
        "sum": partial(np.sum, axis=1),                                         # Sum of the rank for each student
        "mean": lambda mat: [np.mean(row[row!=0]) for row in mat],              # Mean of the rank for each student
        "var": lambda mat: [np.var(row[row!=0]) for row in mat],                # Variance of the rank for each student
        "std": lambda mat: [np.std(row[row!=0]) for row in mat],                # Standard deviation of the rank
        "median": lambda mat: [np.median(row[row!=0]) for row in mat],          # median (2nd quartile) of the rank
        "q1": lambda mat: [np.quantile(row[row!=0], q=0.25) for row in mat],    # 1st quartile of the rank
        "q3": lambda mat: [np.quantile(row[row!=0], q=0.75) for row in mat],    # 3rd quartile of the rank
        "n": partial(np.count_nonzero, axis=1),                                 # Number of subject ranked for each student
        "firstRank": lambda mat: [np.min(row[row!=0]) for row in mat],          # First rank granted
        "lastRank": partial(np.max, axis=1)                                     # Last rank granted
    }
    
    # Add external function and compute all the requested functions
    fncs.update(additional_fnc) 
    df = pd.DataFrame(columns=fncs.keys())
    for key, value in fncs.items():
        df[key] = value(rankMatrix)
    
    # Set up the post-processing function (aggregation operations over columns), in a list such that it is possible to chain multiple level of operations and intermediate ones
    post_fncs = [{}]
    
    # Add the different level of external post aggregation functions.
    for postAggregation in post_aggregation_fnc:
        post_fncs.append(postAggregation)
    
    # Apply functions 
    for post in post_fncs:
        for key, value in post.items():
            df[key] = value(df)
    
    # Return the dataframe
    return df

def getAdditionalPreferencesBasedFunction(preferences:pd.DataFrame) -> dict[str, partial | Callable]:
    return {
        "minStudentRank": lambda mat: preferences.loc[:,preferences.columns.str.startswith("Rg")].min(axis=1),
        "maxStudentRank": lambda mat: preferences.loc[:,preferences.columns.str.startswith("Rg")].max(axis=1),
        "requested": lambda mat: preferences["maxOptional"].to_numpy()
    }

def getAdditionalPreferencesBasedPostFunction() -> tuple[dict[str, partial | Callable], ...]:
    return ({
        "rankedVSrequested": lambda dataframe: dataframe["n"]-dataframe["requested"],
        "maxRankDistance": lambda dataframe: (dataframe["maxStudentRank"]-dataframe["lastRank"])/dataframe["maxStudentRank"],
        "minRankDistance": lambda dataframe: (dataframe["firstRank"]-dataframe["minStudentRank"])/dataframe["firstRank"]
    },) # Do not remove the coma, it is here to make the thing a tuple

if __name__ == "__main__":
    # Get datasets
    affectations, preferences, courses = getData(DEFAULT_AFFECTATIONS_PATH, DEFAULT_PREFERENCES_PATH, DEFAULT_COURSES_PATH)
    
    # Computer the rank matrix
    rankMatrix = computeRankMatrix(affectations, preferences)

    # Provide external functions and compute the metrics for students
    additional_fncs = getAdditionalPreferencesBasedFunction(preferences)
    additional_post_fncs = getAdditionalPreferencesBasedPostFunction()
    computeBaseMetrics(rankMatrix, additional_fncs,*additional_post_fncs, onStudent=True)
    
    # On the lectures
    additional_fncs = {"spots": lambda mat: courses["spots"].to_numpy()}
    additional_post_fncs = ({"freeSpots":lambda dataframe: np.max(np.array([dataframe["spots"]-dataframe["n"],np.zeros(dataframe.shape[0])], dtype=int), axis=0)},) # Do not remove the coma, it is here to make the thing a tuple
    computeBaseMetrics(rankMatrix, additional_fncs, *additional_post_fncs, onStudent=False)