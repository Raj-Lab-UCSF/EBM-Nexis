import os
import numpy as np
import scipy as sp
import scipy.io
from scipy.linalg import expm
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import odeint

class run_Nexis:
    def __init__(self,C_,U_,t_vec_,w_dir_=0,volcorrect_=0,region_volumes_=[],parameters_ =[]):
        self.C = C_ # Connectivity matrix, nROI x nROI
        self.U = U_ # Matrix or vector of cell type or gene expression, nROI x nTypes
        self.t_vec = t_vec_ # Vector of time points to output model predictions, 1 x nt
        self.volcorrect = volcorrect_ # Binary flag indicating whether to use volume correction - ask ben 
        self.w_dir = w_dir_ # Binary flag indicating whether to use directionality or not 
        self.region_volumes = region_volumes_ # Array of region volumes, nROI x 1 if applicable 
        self.parameters = parameters_ # Fixed model parameters 

    def inverse_nexis(self, time_point, subject_tau, tau_threshold, eigen_threshold): 
        # tau_threshold is the percentile under which all regions are sent to 0
        # time_poaint is the time point available for subject s
        # subject_tau is a vector containing the values of tau in every region at that time point
        # eigen_threshold is percentile over which eigen values are removed
        """
        Returns initial vector x0 given fixed model parameters

        """
        # Define parameters
        ntypes = np.size(self.U,axis=1)
        alpha = self.parameters[0] # global connectome-independent growth (range [0,5])
        beta = self.parameters[1] # global diffusivity rate (range [0,5])
        #if self.use_baseline:
            #gamma = 1
        #else:
            #gamma = self.parameters[2] # seed rescale value (range [0,10])
        if self.w_dir==0:
            s = 0.5
        else:
            s = self.parameters[3] # directionality (0 = anterograde, 1 = retrograde)
        b = np.transpose(self.parameters[4:(ntypes+4)]) # cell-type-dependent spread modifier (range [-5,5])
        p = np.transpose(self.parameters[(ntypes+4):6]) # cell-type-dependent growth modifier (range [-5,5]) 
        
        # Define starting pathology x0
                
        # Define diagonal matrix Gamma containing spread-independent terms
        s_p = np.dot(self.U,p)
        Gamma = np.diag(s_p) + (alpha * np.eye(len(s_p))) 

        # Define Laplacian matrix L
        C_dir = (1-s) * np.transpose(self.C) + s * self.C
        coldegree = np.sum(C_dir,axis=0)
        L_raw = np.diag(coldegree) - C_dir
        s_b = np.dot(self.U,b)
        s_b = np.reshape(s_b,[len(s_b),1])
        S_b = np.tile(s_b,len(s_b)) + np.ones([len(s_b),len(s_b)])
        L = np.multiply(L_raw,np.transpose(S_b))

        # Apply volume correction if applicable
        if self.volcorrect:
            voxels_2hem = self.region_volumes

            inv_voxels_2hem = np.diag(np.squeeze(voxels_2hem).astype(float) ** (-1))
            
            L = np.mean(voxels_2hem) * np.dot(inv_voxels_2hem,L)

        # Define system dydt = Ax
        A = Gamma - (beta * L)

        #Solve
        x0 = self.run_inverse(A, subject_tau, time_point, tau_threshold,eigen_threshold)

        return x0

    def run_inverse(self,A, subject_tau, time_point, tau_threshold,eigen_threshold):
    
        # Eigen decomposition of A
        eigenvalues, eigenvectors = np.linalg.eig(A)  

        # Remove the highest eigen values based on eigen_threshold
        if eigen_threshold == 100:
            # If the threshold is 100, include all eigenvalues
            mask = np.ones_like(eigenvalues, dtype=bool)
        else:
            # Calculate the threshold eigenvalue based on the given percentile
            eigen_percentile = np.percentile(eigenvalues, eigen_threshold)
            mask = eigenvalues < eigen_percentile      
        eigen_val_thresholded = eigenvalues[mask]
        eigen_vec_thresholded = eigenvectors[:, mask]   

        # Projection into eigen space
        x_eigen = np.dot(eigen_vec_thresholded.T, subject_tau)

        # Loop through eigenvalues
        q = np.zeros((len(eigen_val_thresholded), 1))
        for i in range(len(eigen_val_thresholded)):
            qi = np.exp(time_point * eigen_val_thresholded[i]) * x_eigen[i]
            q[i] = qi

        x0 = np.dot(eigen_vec_thresholded, q)

        # Threshold x0 vector such that any value < the threshold is set to 0
        tau_percentile = np.percentile(x0, tau_threshold)
        x0_thresholded = x0.copy()  
        x0_thresholded[x0 < tau_percentile] = 0

        return x0_thresholded
