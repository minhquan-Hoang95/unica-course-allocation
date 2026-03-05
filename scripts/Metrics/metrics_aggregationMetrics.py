# Make aggregation like sum of sum rank, mean of sum rank, mean of last rank, etc.
import metrics_utils as mu
import pandas as pd
from typing import Callable, Optional
from functools import partial
from scipy import stats

DEFAULT_OUT_COURSES_METRICS_PATH = "out/coursesMetrics.csv"
DEFAULT_OUT_STUDENTS_METRICS_PATH = "out/studentsMetrics.csv"

def getVectorsFromCSV(*paths:str) -> tuple[pd.DataFrame, ...]:
    return tuple([pd.read_csv(path) for path in paths])

def getBaseAggregationMetrics(vectors:pd.DataFrame,
                                additional_fnc:Optional[dict[str, partial | Callable]] = None,
                                *post_aggregation_fnc:dict[str, partial | Callable]
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
    df = vectors.iloc[:,1:].copy(deep=True)
    # Get first metrics
    described_df = df.describe(include="all", percentiles=[i/100 for i in range(5,100,5)])
    
    # Apply additional functions
    for key, value in additional_fnc.items():
        try:
            described_df.loc[key,:] = value(df)
        except TypeError:
            described_df.loc[key,described_df.dtypes!="object"] = value(df.loc[:,df.dtypes!="object"])
    
    # Set up the post-processing function (aggregation operations over columns), in a list such that it is possible to chain multiple level of operations and intermediate ones
    post_fncs = [{}]
    
    # Add the different level of external post aggregation functions.
    for postAggregation in post_aggregation_fnc:
        post_fncs.append(postAggregation)
    
    # Apply functions 
    for post in post_fncs:
        for key, value in post.items():
            described_df.loc[key,:] = value(described_df)
    
    return described_df

def getAdditionalAggregationFunctions() -> dict[str, Callable | partial]:
    """Additional aggregations functions for the `getBaseAggregationMetrics` function. It includes the ***skewness*** (measure of assymetry based on moments), the 
    ***kurtosis*** (how flat is the distribution).

    Returns:
        dict[str, Callable | partial]: A dictionary of function to feed in `getBaseAggregationMetrics`. 
    """
    return {
        "Skewness": partial(stats.skew, bias=True),
        "Kurtosis": partial(stats.kurtosis, bias=True)
    }

def getAdditionalAggregationPostFunctions() -> tuple[dict[str, Callable | partial]]:
    """Additional Post aggregation functions to feed in `getBaseAggregationMetrics`. It includes the ***IQR*** (Inter Quartile Range) and the 
    ***Yule Assymetry*** (measure of assymetry based on quantile).

    Returns:
        tuple[dict[str, Callable | partial]]: A tuple containing the functions to feed.
    """
    return ({
        "IQR":lambda dataframe: dataframe.loc["75%",:]-dataframe.loc["25%",:]
    }, {
        "Yule_assymetry":lambda dataframe: (dataframe.loc["25%",:] + dataframe.loc["75%",:] - 2*dataframe.loc["50%",:])/dataframe.loc["IQR",:]
    })

if __name__ == "__main__":
    # Get the vectors
    coursesVectors, studentsVectors = getVectorsFromCSV(mu.DEFAULT_OUT_COURSES_VEC_PATH, mu.DEFAULT_OUT_STUDENTS_VEC_PATH)
    
    # Get the additional functions
    additional_fncs = getAdditionalAggregationFunctions()
    additional_post_fncs = getAdditionalAggregationPostFunctions()
    
    # Computes Metrics for courses
    getBaseAggregationMetrics(coursesVectors, additional_fncs, *additional_post_fncs).to_csv(DEFAULT_OUT_COURSES_METRICS_PATH)
    
    # Compute metrics for students
    getBaseAggregationMetrics(studentsVectors, additional_fncs, *additional_post_fncs).to_csv(DEFAULT_OUT_STUDENTS_METRICS_PATH)