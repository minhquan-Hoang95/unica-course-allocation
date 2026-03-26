import os
import sys
import tempfile

import numpy as np
import pandas as pd

# Ajouter le chemin vers scripts/Metrics pour pouvoir importer les modules
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts/Metrics"))
)

import metrics_aggregationMetrics as mam
import metrics_utils as mu


def test_computeRankMatrix():
    # Créer des données de test
    affectations = pd.DataFrame(
        {"studentID": [1, 2], "c1": [1, 0], "c2": [0, 1], "c3": [1, 1]}
    )
    preferences = pd.DataFrame(
        {"studentID": [1, 2], "Rg1": [1, 10], "Rg2": [2, 20], "Rg3": [3, 30]}
    )

    # Appeler la fonction
    result = mu.computeRankMatrix(affectations, preferences)

    # Vérifier le résultat
    # Pour étudiant 1: c1=1*Rg1=1, c2=0*Rg2=0, c3=1*Rg3=3 -> [1, 0, 3]
    # Pour étudiant 2: c1=0*Rg1=10, c2=1*Rg2=20, c3=1*Rg3=30 -> [0, 20, 30]
    expected = np.array([[1, 0, 3], [0, 20, 30]])

    np.testing.assert_array_equal(result, expected)


def test_getStudentsTrackFromPreferences():
    preferences = pd.DataFrame(
        {"studentID": [1, 2], "math_track": [1, 0], "cs_track": [0, 1]}
    )

    result = mu.getStudentsTrackFromPreferences(preferences)
    assert result == ["math_track", "cs_track"]


def test_computeBaseVectors():
    rankMatrix = np.array([[1, 0, 3], [0, 2, 4]])

    result = mu.computeBaseVectors(rankMatrix)

    # Vérifier quelques colonnes
    assert "sum" in result.columns
    assert "mean" in result.columns

    # Étudiant 1: [1, 3] (on ignore le 0) -> sum=4, mean=2
    # Étudiant 2: [2, 4] (on ignore le 0) -> sum=6, mean=3
    assert result["sum"].tolist() == [4, 6]
    assert result["mean"].tolist() == [2.0, 3.0]


def test_getBaseAggregationMetrics():
    vectors = pd.DataFrame(
        {"studentID": [1, 2, 3], "metric1": [10, 20, 30], "metric2": [5, 15, 25]}
    )

    result = mam.getBaseAggregationMetrics(vectors)

    assert "mean" in result.index
    assert result.loc["mean", "metric1"] == 20.0
    assert result.loc["mean", "metric2"] == 15.0


def test_save_results():
    # Test de la "sauvegarde" (export CSV)
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test_save.csv")
        df.to_csv(file_path, index=False)

        assert os.path.exists(file_path)
        loaded_df = pd.read_csv(file_path)
        pd.testing.assert_frame_equal(df, loaded_df)
