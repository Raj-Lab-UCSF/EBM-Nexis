import os
import numpy as np
import scipy as sp
import scipy.io
from scipy.linalg import expm
import pandas as pandas
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from scipy.optimize import minimize

# Function to generate heat map of NEXIS output 
def heatmap(init_vec_method, Y):
    if init_vec_method == 'baseline':
        plt.imshow(Y, cmap='viridis', interpolation='none', aspect='auto')

    else: 
        # Exclude binary seeding location for binary initial vector so it does not drown out the signal in other regions (EDIT SEEDING LOCATION HERE)
        Y_modified = np.delete(Y, [14,48], axis=0) # NEED TO CHANGE for different seeding regions or different list of total regions
        plt.imshow(Y_modified, cmap='viridis', interpolation='none', aspect='auto')
        
    plt.colorbar()  # Add a color bar to map colors to values
    plt.title('Nexis Heatmap of Tau Time Series Across Regions')
    return plt


# Function to normalize by L2 norm
def normalize_by_l2_norm(matrix):
    l2_norms = np.linalg.norm(matrix, axis=1, keepdims=True)  # Calculate L2 norm for each row
    normalized_matrix = matrix / l2_norms  # Normalize each row by its L2 norm
    return normalized_matrix


# Function to calculate mean squared error
def mse_matrix(matrix1,matrix2):
    # Ensure the matrices have the same shape
    if matrix1.shape != matrix2.shape:
        raise ValueError("Matrices must have the same dimensions")
    return np.mean((matrix1 - matrix2) ** 2) 


# Error function
def Nexis_error(params, patient_tau, stages, nexis_model):
    
    param1, param2, param3, param4, param5, param6 = params 
    # param1 = alpha, param2 = beta, param3 = gamma, param4 = b, param5 = p, param6 = k

    # Parameters for simulate_nexis method
    parameters = [param1, param2, param3, 0.5, param4, param5, param6]  # [alpha, beta, gamma, s, b, p , k] 

    # Call the simulate_nexis method with the parameters
    Y = nexis_model.simulate_nexis(parameters)

    # For optimization, only take stages from Y that correspond to patient's stages 
    Y_edited = Y[:, stages]

    error = mse_matrix(patient_tau, Y_edited)
    
    return error