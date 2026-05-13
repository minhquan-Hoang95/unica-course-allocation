import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots


def print_summary(df):
    print(df.describe())


def print_columns(df):
    print(df.columns)


def create_box_plot(df, title, feature):
    fig = px.box(df, y=feature, title=title)
    fig.write_html("graphics/" + title + ".html")


def create_histogram(df, title, feature):
    fig = px.histogram(df, x=feature, title=title)
    fig.write_html("graphics/" + title + ".html")


def create_IQR_column(df):
    df["IQR"] = df["q3"] - df["q1"]
    return df


def create_occupancy_column(df_cours):
    df_cours["occupancy"] = (df_cours["spots"] - df_cours["freeSpots"]) / df_cours[
        "spots"
    ]
    return df_cours


def create_rank_distance_comparison(df_student):

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=(
            "MinRankDistance",
            "MaxRankDistance",
            "correctedMaxRankDistance",
        ),
    )

    fig.add_trace(
        go.Box(y=df_student["minRankDistance"], name="MinRankDistance"), row=1, col=1
    )

    fig.add_trace(
        go.Box(y=df_student["maxRankDistance"], name="MaxRankDistance"), row=1, col=2
    )

    fig.add_trace(
        go.Box(
            y=df_student["correctedMaxRankDistance"], name="correctedMaxRankDistance"
        ),
        row=1,
        col=3,
    )

    fig.update_layout(title="Rank Distance Comparison")

    fig.write_html("graphics/rank_distance_comparison.html")


def course_pop_capacity_use(df_cours):
    fig = px.scatter(
        df_cours, x="median", y="occupancy", title="Course Capacity vs Occupancy"
    )
    fig.write_html("graphics/course_capacity_vs_occupancy.html")


if __name__ == "__main__":
    pio.renderers.default = "browser"

    df_cours = pd.read_csv("data/coursesMetrics.csv")
    df_student = pd.read_csv("data/studentMetrics.csv")

    df_student = create_IQR_column(df_student)

    df_cours = create_occupancy_column(df_cours)
    df_cours = create_IQR_column(df_cours)

    # create_box_plot(df_cours, "cours_occupancy", "occupancy")
    course_pop_capacity_use(df_cours)
    # create_histogram(df_cours, "cours_occupancy", "occupancy")
    # create_rank_distance_comparison(df_student)
    # create_box_plot(df_student, "mean_student_metrics", "mean")
    # create_histogram(df_student, "Distribution of median student metrics", "median")
    # print_columns(df_cours)
    # print(df_student["minStudentRank"].value_counts())
    # print(df_student["maxStudentRank"].value_counts())
