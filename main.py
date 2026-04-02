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
    
    Parameters:
        training_hours (array): X values
        running_times (array): y values
        model_name (str): file name
        degree (int): polynomial degree (default 3)
    
    Returns:
        trained model
    """
    if len(training_hours) != len(running_times):
        raise ValueError("training_hours and running_times must have same length")

    X = np.array(training_hours).reshape(-1, 1)
    Y = np.array(running_times)

    model = Pipeline([
        ("poly", PolynomialFeatures(degree=degree)),
        ("linear", LinearRegression())
    ])

    model.fit(X, Y)
    joblib.dump(model, model_name)
    print(f"Model saved to {model_name}")

    return model


def predict_from_model(model_name, hours_value):
    """
    Loads model and predicts running time for given hours.
    
    Parameters:
        model_name (str): file name of saved model
        hours_value (float): training hours value
    
    Returns:
        float: predicted running time (min 0.0)
    """
    model = joblib.load(model_name)
    X_new = np.array([[hours_value]])
    prediction = model.predict(X_new)
    
    return float(max(0.0, prediction[0]))


def get_model_accuracy(model_name, training_hours, running_times):
    """
    Calculate R² accuracy score for trained model.
    
    Parameters:
        model_name (str): file name of saved model
        training_hours (array): X values
        running_times (array): y values
    
    Returns:
        float: R² score
    """
    model = joblib.load(model_name)
    X = np.array(training_hours).reshape(-1, 1)
    Y = np.array(running_times)
    
    score = model.score(X, Y)
    return float(score)


if __name__ == "__main__":
    # Example dataset
    training_hours = np.array([2, 3, 5, 7, 9, 12, 16, 20, 25, 30]).reshape(-1, 1)
    running_times = np.array([95, 85, 70, 65, 60, 55, 50, 53, 58, 70])
    
    # Train and save
    train_and_save_model(training_hours, running_times, "running_model.joblib", degree=3)
    
    # Predict example
    result = predict_from_model("running_model.joblib", 15)
    print(f"Predicted running time for 15 training hours: {result}")
    
    # Get accuracy
    accuracy = get_model_accuracy("running_model.joblib", training_hours, running_times)
    print(f"Model R² score: {accuracy}")
