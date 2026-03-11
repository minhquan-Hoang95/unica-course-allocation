import pandas as pd
import numpy as np
from typing import Optional, Callable
from functools import partial
import json

DEFAULT_IN_AFFECTATIONS_PATH = "srcFiles/FCFSaffectation.csv"
DEFAULT_IN_PREFERENCES_PATH = "srcFiles/studentsRandom.csv"
DEFAULT_IN_COURSES_PATH = "srcFiles/courses.csv"
DEFAULT_IN_PARAMETERS_PATH = "srcFiles/parameters.json"

DEFAULT_OUT_COURSES_VEC_PATH = "out/coursesVectors.csv"
DEFAULT_OUT_STUDENTS_VEC_PATH = "out/studentsVectors.csv"



def getData(*paths:str) -> tuple[pd.DataFrame, ...]:
    return tuple([pd.read_csv(path) for path in paths])

def getParameters(path:str) -> dict:
    with open(path) as file:
        return json.load(file)

def computeRankMatrix(affectations:pd.DataFrame, preferences:pd.DataFrame) -> np.ndarray:
    # Crop to the necessary information
    affectationsMatrix = affectations.loc[:,affectations.columns.str.startswith("c")].to_numpy()
    preferencesMatrix = preferences.loc[:,preferences.columns.str.startswith("Rg")].to_numpy()
    
    # Return the matrix of selected ranked preferences
    return affectationsMatrix*preferencesMatrix

# Just an helper function
def getStudentsTrackFromPreferences(preferences:pd.DataFrame) -> list[str]:
    # Get all the column that concern tracks
    trackCols = preferences.loc[:,preferences.columns.str.endswith("track")]
    
    # Get the track name of each student, then return it
    trackIndices = np.where(trackCols.to_numpy()==True)[1]
    return [trackCols.columns[i] for i in trackIndices]

# Just an helper function
def getStudentsMandatoryLecturesFromTrack(courses:pd.DataFrame, studentsTrack:list[str]) -> list[list[str]]:
    # Get the list of mandatory courses for each student depending on its track
    mandatoryCourses = []
    for track in studentsTrack:
        # Get the course for each tracks
        trackCourses = courses.loc[courses[track]==True,"courseID"].tolist()
        # Add it to the list of mandatory course with Rg[x] for each course so that it is easier to interact with the preferences dataframe afterward
        mandatoryCourses.append(list(map(lambda x: f"Rg{x}", trackCourses)))
    return mandatoryCourses

def computeBaseVectors(rankMatrix:np.ndarray,
                       additional_fnc:Optional[dict[str, partial | Callable]] = None,
                       *post_df_fnc:dict[str, partial | Callable],
                       onStudent:bool = True
                       ) -> pd.DataFrame:
    """Function that compute the basic statistics values on the ranks. This include the sum, mean, var, std, median, quartiles, n, the first and last rank granted.
    It is possible to include others functions.
    
    **Warning: You can provide external functions, but there is no warranty they will work properly.**

    Args:
        rankMatrix (np.ndarray): The matrix of rank
        onStudent (bool): If True compute the statistics on the student, otherwise on the lectures. Defaults to True
        additional_fnc (Optional[dict[str,partial[np.ndarray] | Callable]], optional): External functions acting on the rank matrix. Defaults to None.
        *post_df_fnc (tuple[dict[str,partial[np.ndarray]|Callable]]): External functions acting on the dataframe, after the first metrics were computed. Useful for metametrics.

    Returns:
        pd.DataFrame: A dataframe formed by a column for each function and a row for each student.
    """
    
    # Prepare external functions
    if additional_fnc is None:
        additional_fnc = {}
    if post_df_fnc is None:
        post_df_fnc = ()
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
    for postAggregation in post_df_fnc:
        post_fncs.append(postAggregation)
    
    # Apply functions 
    for post in post_fncs:
        for key, value in post.items():
            df[key] = value(df)
    
    # Return the dataframe
    return df

def getAdditionalPreferencesBasedOnStudentsFunction(preferences:pd.DataFrame) -> dict[str, partial | Callable]:
    """Additional function for `computeBaseVectors` including ***minStudentRank*** (the minimum normalised rank for the student; depends on mandatory lectures quantity),
    ***maxStudentRank*** (the maximum normalised rank for the student; depend on the number of additional optional lectures), and ***requested*** the number of course the student has requested.
    
    The track of the student is also explicited.

    Args:
        preferences (pd.DataFrame): The DataFrame of preferences

    Returns:
        dict[str, partial | Callable]: A dict of functions to feed in `computeBaseVectors`
    """
    return {
        "minStudentRank": lambda mat: preferences.loc[:,preferences.columns.str.startswith("Rg")].min(axis=1),
        "maxStudentRank": lambda mat: preferences.loc[:,preferences.columns.str.startswith("Rg")].max(axis=1),
        "requested": lambda mat: preferences["maxOptional"].to_numpy(),
        "track": lambda mat: getStudentsTrackFromPreferences(preferences)
    }

def getAdditionalCoursesBasedOnStudentsFunction(preferences:pd.DataFrame, courses:pd.DataFrame, parameters:dict) -> dict[str, partial | Callable]:
    """Make additional function to use in `computeBaseVectors`. This include the ***mandatoryCorrectedRankSum*** (RankSum minus the rank of mandatory lectures), the ***optionalCorrectedRankSum*** (RankSum minus the rank of additional optional lectures, i.e. we keep only the minimal number of lecture to pass the semester),
     the ***correctedRankSum*** (RankSum minus both corrections). Finally, it also include the rank of the last subject required to pass the semester (which can be an optional or a mandatory subject): ***lastMandatoryOptionalRank***. From the sum, other measures are derived such as the variance and the standard deviation. 
     Additionally, a correction on the median and the quantile are also given.

    Args:
        preferences (pd.DataFrame): The dataframe of preferences
        courses (pd.DataFrame): The dataframe of courses (to get mandatory subjects)
        parameters (dict): The parameters (the dictionary including the number of minimal subject for each specialities)

    Returns:
        dict[str, partial | Callable]: A dictionary of additional function for `computeBaseVectors`. 
    """
    # Get the the track for each student
    studentTrack = getStudentsTrackFromPreferences(preferences)
    # Get the set of mandatory lectures for each student based on the track
    mandatoryLectures = getStudentsMandatoryLecturesFromTrack(courses, studentTrack)
    # Get the minimum number of lecture to pass the semester for each track (usually 7 including mandatory lectures)
    minNj = np.array([parameters["spe"][track]["minNj"] for track in studentTrack])
    
    def countMandatoryOptional(mat:np.ndarray):
        # Count the number of mandatory lectures
        mandatoryCount = np.array(list(map(lambda i: len(i), mandatoryLectures)))
        # Get the number of mandatory optional lectures (the minimum number of lecture to pass the semester)
        return  minNj + mandatoryCount
    
    # Correct the sumRank wrt the mandatory lecture sum rank (we remove the rank of mandatory lectures in the count)
    def mandatoryRankCorrection(mat:np.ndarray):
        # Compute the sumRank
        rankSum = np.array([np.sum(row[row!=0]) for row in mat])
        
        # For each student compute the correction
        mandatoryCorrection = []
        for studentID, lecture in enumerate(mandatoryLectures, start=1):
            # If there is no mandatory lecture, do not apply correction and skip
            if lecture == []: 
                mandatoryCorrection.append(0)
                continue
            
            # If there is mandatory lectures, create the correction as the sum of mandatory lectures rank
            rankCorrection = preferences.loc[preferences["studentID"]==studentID, lecture].to_numpy().sum()
            mandatoryCorrection.append(rankCorrection)
        
        # Apply the correction to the sum of the rank and apply it.
        return (rankSum - np.array(mandatoryCorrection)).tolist()
    
    # Correct the sumRank wrt the number of optional lecture the student takes (do not need to take into account optional lectures in rankSum, it falsify the rankSum)
    def optionalRankCorrection(mat:np.ndarray):
        # Compute the rankSum
        rankSum = np.array([np.sum(row[row!=0]) for row in mat])
        
        # Get the number of mandatory optional lectures (the minimum number of lecture to pass the semester)
        mandatoryOptional = countMandatoryOptional(mat)
        
        # Compute the correction
        correction = []
        for studentID, row in enumerate(mat):
            # We sum the rank after the minimum number of lectures to complete
            correction.append(sum(sorted(row[row!=0])[mandatoryOptional[studentID]:]))
        
        # Apply the correction
        return (rankSum - np.array(correction)).tolist()
    
    # Merges the two above corrections  
    def allCorrection(mat:np.ndarray):
        rankSum = np.array([np.sum(row[row!=0]) for row in mat])
        mandatoryCorrection = rankSum - np.array(mandatoryRankCorrection(mat))
        optionalCorrection = rankSum - np.array(optionalRankCorrection(mat))
        return rankSum - (mandatoryCorrection + optionalCorrection)
    
    # Get the last rank of the mandatory optional lecture (we do not really cares of the rank after the minimal number of lectures)
    def lastMandatoryOptionalRank(mat:np.ndarray):
        # Count optional and mandatory lectures
        mandatoryOptional = countMandatoryOptional(mat)
        
        # Get the last mandatory optional lecture rank
        lastMandatoryOptionalRank = []
        for studentID, row in enumerate(mat):
            # Get last attributed
            lastMandatoryOptionalRank.append(sorted(row[row!=0])[mandatoryOptional[studentID]-1])

        return lastMandatoryOptionalRank

    # Get quantile correction
    def optionalCorrectedQuantile(mat:np.ndarray, quantile:float):                        
        # Get the number of mandatory optional lectures (the minimum number of lecture to pass the semester)
        mandatoryOptional = countMandatoryOptional(mat)
        
        # Initialise the coreected quantile
        rankQuantile = []
        for studentID, row in enumerate(mat):
            # Compute the corrected quantile
            rankQuantile.append(np.quantile(np.sort(row[row!=0])[:mandatoryOptional[studentID]], quantile))
        
        return rankQuantile
    
    # Merges the two above corrections  
    def allCorrection(mat:np.ndarray):
        rankSum = np.array([np.sum(row[row!=0]) for row in mat])
        mandatoryCorrection = rankSum - np.array(mandatoryRankCorrection(mat))
        optionalCorrection = rankSum - np.array(optionalRankCorrection(mat))
        return rankSum - (mandatoryCorrection + optionalCorrection)
    
    # Get the mean correction
    def optionalCorrectedMean(mat:np.ndarray):
        mandatoryOptional = countMandatoryOptional(mat)
        return np.array(optionalRankCorrection(mat))/mandatoryOptional
    
    # Get the Variance correction
    def optionalCorrectedVar(mat:np.ndarray):
        mandatoryOptional = countMandatoryOptional(mat)
        # E(X²)-E(X)²
        return optionalRankCorrection(mat**2)/mandatoryOptional - optionalCorrectedMean(mat)**2
    
    # Just the root of the corrected var
    def optionalCorrectedStd(mat:np.ndarray):
        return np.sqrt(optionalCorrectedVar(mat))
    
    # Return all the functions
    return ({
        "mandatoryCorrectedRankSum": mandatoryRankCorrection,
        "optionalCorrectedRankSum": optionalRankCorrection,
        "correctedRankSum": allCorrection,
        "lastMandatoryOptionalRank": lastMandatoryOptionalRank,
        "optionalCorrectedQ1": partial(optionalCorrectedQuantile, quantile=0.25),
        "optionalCorrectedMedian": partial(optionalCorrectedQuantile, quantile=0.5),
        "optionalCorrectedQ3": partial(optionalCorrectedQuantile, quantile=0.75),
        "optionalCorrectedMean": optionalCorrectedMean,
        "optionalCorrectedVar": optionalCorrectedVar,
        "optionalCorrectedStd": optionalCorrectedStd
    })

def getAdditionalPostOnStudentsFunction() -> tuple[dict[str, partial | Callable], ...]:
    """Additional post processing functions to use in `computeBaseVectors`. It includes ***rankedVSrequested*** (the number of subject which was not granted despite request), ***maxRankDistance*** (The distance between the last granted rank and the last rank that could have been granted),
    ***minRankDistance*** (same, but with the minimal rank). Additionally, it also provides an alternative metric ***correctedMaxRankDistance*** which compute the rank distance between the last course required to pass the semester and the worst that could have been given. Additionally, include
    corrected versions of some metrics. 

    Returns:
        tuple[dict[str, partial | Callable], ...]: A tuple to feed into `computeBaseVectors`.
    """
    # Note: this is a tuple because we can chain operations sequentially
    return ({
        "rankedVSrequested": lambda dataframe: list(map(lambda x:min(x,0), dataframe["n"]-dataframe["requested"])),
        "maxRankDistance": lambda dataframe: (dataframe["maxStudentRank"]-dataframe["lastRank"])/dataframe["maxStudentRank"],
        "minRankDistance": lambda dataframe: (dataframe["firstRank"]-dataframe["minStudentRank"])/dataframe["firstRank"],
        "correctedMaxRankDistance": lambda dataframe: (dataframe["maxStudentRank"]-dataframe["lastMandatoryOptionalRank"])/dataframe["maxStudentRank"],
        "IQR": lambda dataframe: dataframe["q3"]-dataframe["q1"],
        "optionalCorrectedIQR": lambda dataframe: dataframe["optionalCorrectedQ3"]-dataframe["optionalCorrectedQ1"]
    },
    {
        "Yule_assymetry": lambda dataframe: (dataframe["q1"] + dataframe["q3"] - 2*dataframe["median"])/dataframe["IQR"],
        "optionalCorrectedYule_assymetry": lambda dataframe: (dataframe["optionalCorrectedQ1"] + dataframe["optionalCorrectedQ3"] - 2*dataframe["optionalCorrectedMedian"])/dataframe["optionalCorrectedIQR"]
    }       
    )

def getAdditionalCourseBasedOnCoursesFunction(courses:pd.DataFrame) -> dict[str, partial | Callable]:
    """Additional functions for courses to feed in `computeBaseVectors`. It includes the number of available ***spots*** for each lecture.

    Args:
        courses (pd.DataFrame): The dataframe of courses

    Returns:
        dict[str, partial | Callable]: A dictionary of function to feed in `computeBaseVectors`
    """
    return {
        "spots": lambda mat: courses["spots"].to_numpy()
    }
    
def getAdditionalPostCourseBasedOnCoursesFunction() -> tuple[dict[str, partial | Callable], ...]:
    """Additional Post processing functions for courses to feed in `computeBaseVectors`. It includes the number of ***free spots*** for each lecture and the ***loadBalancingDifference*** defined as $diff(j\\in M) = n_m - \\frac{\\sum_{i=1}^m{n_i}}{m}$. See the load balancing problem (here it is a variant, so it might not possess the right information in fine.).

    Returns:
        tuple[dict[str, partial | Callable], ...]: A tuple of function to feed in `computeBaseVectors`.
    """
    return ({
        "freeSpots":lambda dataframe: np.max(np.array([dataframe["spots"]-dataframe["n"],np.zeros(dataframe.shape[0])], dtype=int), axis=0),
        "loadBalancingDifference":lambda dataframe: dataframe["n"] - dataframe["n"].sum()/dataframe.shape[0]
        },) # Do not remove the coma, it is here to make the thing a tuple

if __name__ == "__main__":
    # Get datasets
    affectations, preferences, courses = getData(DEFAULT_IN_AFFECTATIONS_PATH, DEFAULT_IN_PREFERENCES_PATH, DEFAULT_IN_COURSES_PATH)
    parameters = getParameters(DEFAULT_IN_PARAMETERS_PATH)
    
    # Computer the rank matrix
    rankMatrix = computeRankMatrix(affectations, preferences)

    # Provide external functions and compute the metrics for students
    additional_fncs = getAdditionalPreferencesBasedOnStudentsFunction(preferences) | getAdditionalCoursesBasedOnStudentsFunction(preferences, courses, parameters)
    additional_post_fncs = getAdditionalPostOnStudentsFunction()
    computeBaseVectors(rankMatrix, additional_fncs, *additional_post_fncs, onStudent=True).to_csv(DEFAULT_OUT_STUDENTS_VEC_PATH)
    
    # On the lectures
    additional_fncs = getAdditionalCourseBasedOnCoursesFunction(courses)
    additional_post_fncs = getAdditionalPostCourseBasedOnCoursesFunction()
    computeBaseVectors(rankMatrix, additional_fncs, *additional_post_fncs, onStudent=False).to_csv(DEFAULT_OUT_COURSES_VEC_PATH)