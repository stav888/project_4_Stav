"""
Machine Learning Module - Train and Predict Running Times
Polynomial Regression model for predicting running times based on training hours.
"""

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures


def train_and_save_model(training_hours, running_times, model_name, degree=3):
    """
    Trains a polynomial regression model and saves it.

    Args:
        training_hours (list): X values (training hours)
        running_times (list): Y values (running times)
        model_name (str): file name (e.g., "john.pkl")
        degree (int): polynomial degree (default 3)

    Returns:
        trained model

    Raises:
        ValueError: if training_hours and running_times have different lengths
    """
    if len(training_hours) != len(running_times):
        raise ValueError("training_hours and running_times must have same length")

    # Reshape training_hours for sklearn
    X = np.array(training_hours).reshape(-1, 1)
    Y = np.array(running_times)

    # Create polynomial regression pipeline
    model = Pipeline([
        ("poly", PolynomialFeatures(degree=degree)),
        ("linear", LinearRegression())
    ])

    # Fit the model
    model.fit(X, Y)
    
    # Save to disk
    joblib.dump(model, model_name)
    print(f"Model saved to {model_name}")

    return model


def predict_from_model(model_name, hours_value):
    """
    Loads model and predicts running time.

    Args:
        model_name (str): username / file name (e.g., "john.pkl")
        hours_value (float): number of training hours

    Returns:
        float: predicted running time

    Raises:
        FileNotFoundError: if model file doesn't exist
    """
    model = joblib.load(model_name)
    X_new = np.array([[hours_value]])
    prediction = model.predict(X_new)

    return float(prediction[0])


def get_model_accuracy(model_name, training_hours, running_times):
    """
    Calculates R² score (accuracy) of the trained model.

    Args:
        model_name (str): file name of the model
        training_hours (list): X values used in training
        running_times (list): Y values used in training

    Returns:
        float: R² score between 0 and 1
    """
    model = joblib.load(model_name)
    X = np.array(training_hours).reshape(-1, 1)
    Y = np.array(running_times)
    
    score = model.score(X, Y)
    return float(score)
