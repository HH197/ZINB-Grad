#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 18 15:19:08 2022

@author: hh197

This will contain all of the helper functions. 
"""
import numpy as np
import seaborn as sn
from sklearn import metrics
from sklearn.cluster import KMeans
from matplotlib import pyplot as plt
from pandas import DataFrame
from sklearn.neighbors import NearestNeighbors
import scipy.sparse


def kmeans(data, kmeans_kwargs = {"init": "random", 
                                   "n_init": 50, 
                                   "max_iter": 400, 
                                   "random_state": 197}):
        
    """Performing K-means on the encoded data"""
    
    sil_coeff = []
    
    
    
    for k in range(2, 10):
        kmeans = KMeans(n_clusters=k, **kmeans_kwargs)
        kmeans.fit(data)
        # score = kmeans.inertia_
        score = metrics.silhouette_score(data, kmeans.labels_)
        sil_coeff.append(score)
        
    return sil_coeff

def plot_si(sil_coeff):
        
    """Silhouette plot"""
    
    plt.style.use("fivethirtyeight")
    plt.plot(range(2, 10), sil_coeff)
    plt.xticks(range(2, 10))
    plt.xlabel("Number of Clusters")
    plt.ylabel("Silhouette Coefficient")
    plt.show()
    # plt.savefig(base_dir + 'test1.png')

def plot_loss(losses, xlab = 'Epoch', ylab = 'Neg-Loglikelihood'):
    
    '''
    This function will plot the tracked losses during training. 
    
    Parameters
    ----------
    losses : list 
        The losses.
    
    xlab : str
        The x axis label.
    
    ylab : str
        The y axis label.
    '''
    
    plt.plot(range(len(losses)), losses)
    plt.ylabel(ylab)
    plt.xlabel(xlab)



def measure_q(data, Groups= None, n_clusters=6,  
              
              kmeans_kwargs = {"init": "random", 
                               "n_init": 50, 
                               "max_iter": 400, 
                               "random_state": 197}):
    
    """Measuring the quality of clustering using NMI and confusion matrix"""
    
    kmeans = KMeans(n_clusters, **kmeans_kwargs)
    kmeans.fit(data)
    
    
    Groups = np.ndarray.astype(Groups, np.int)
    NMI = metrics.cluster.normalized_mutual_info_score(Groups, kmeans.labels_)
    print(f'The NMI score is: {NMI}')
    CM = metrics.confusion_matrix(Groups, kmeans.labels_)
    
    df_cm = DataFrame(CM, range(1, CM.shape[0]+1), range(1, CM.shape[1]+1))
    # plt.figure(figsize=(10,7))
    sn.set(font_scale=1.4) # for label size
    sn.heatmap(df_cm, annot=True, annot_kws={"size": 5}) # font size
    
    plt.show()

def corrupting(data, p = 0.10, method = 'Uniform', percentage = 0.10):
    
    '''
    Adopted from the "Deep Generative modeling for transcriptomics data"
    
    This function will corrupt  (adding noise or dropouts) the datasets for
    imputation benchmarking. 
    
    Two different approaches for data corruption: 
        1. Uniform zero introduction: Randomly selected a percentage of the nonzero 
        entries and multiplied the entry n with a Ber(0.9) random variable. 
        2. Binomial data corruption: Randomly selected a percentage of the matrix and
replaced an entry n with a Bin(n, 0.2) random variable.


    Parameters
    ----------
    data : numpy ndarray 
        The data.
        
    p : float >= 0 and <=1
        The probability of success in Bernoulli or Binomial distribution.
        
    method: str 
        Specifies the method of data corruption, one of the two options: "Uniform" and "Binomial"
    
    percentage: float >0 and <1.
        The percentage of non-zero elements to be selected for corruption. 
        
    Returns
    -------
    data_c : numpy ndarray 
        The corrupted data.
    
    x, y, ind : int
        The indices of where corruption is applied. 
    '''
    
    data_c = data.astype(np.int32)
    x, y = np.nonzero(data)
    ind = np.random.choice(len(x), int(0.1 * len(x)), replace=False)
    
    if method == 'Uniform':
        data_c[x[ind], y[ind]] *= np.random.binomial(1, p)
        
    elif method == 'Binomial':
        
        data_c[x[ind], y[ind]] = np.random.binomial(data_c[x[ind], y[ind]].astype(np.int), p)
        
    else:
        raise ValueError('''Method can be one of "Uniform" or "Binomial"''') 
    # to be developed
    
    return data_c.astype(np.float32), x, y, ind

def Eval_Imputation (data, data_imp, x, y, ind):
    
    '''
    Calculates the median L1 distance between the original dataset and the 
    imputed values for corrupted entries only.
    
    Parameters
    ----------
    data : numpy ndarray 
        The data.
        
    data_imp : numpy ndarray 
        The imputed data.
        
    x, y, ind : int
        The indices of where corruption is applied. 
        
    Returns
    -------
    L1 : float
        The median L1 distance between original and imputed datasets at given
    indices.
    '''
    
    L1 = np.median(np.abs(data[x[ind], y[ind]] - data_imp[x[ind], y[ind]]))
    
    return L1
    
def entropy(batches):
    
    '''
    To be added!
    '''    
    n_batches, frq = np.unique(batches, return_counts=True)
    n_batches = len(n_batches)
    frq = frq/np.sum(frq)
    
    # if frequency == 0 or frequency == 1:
    #     return 0
    
    return -np.sum(frq*np.log(frq))



def entropy_batch_mixing(latent_space, 
                         batches, 
                         K = 50, 
                         n_jobs = 8, 
                         n = 100, 
                         n_iter = 50):
    
    '''
    Adopted from:
    
    1) Haghverdi L, Lun ATL, Morgan MD, Marioni JC. Batch effects in
    single-cell RNA-sequencing data are corrected by matching mutual nearest 
    neighbors. Nat Biotechnol. 2018 Jun;36(5):421-427. doi: 10.1038/nbt.4091. 
    
    2) Lopez R, Regier J, Cole MB, Jordan MI, Yosef N. Deep generative 
    modeling for single-cell transcriptomics. Nat Methods. 
    2018 Dec;15(12):1053-1058. doi: 10.1038/s41592-018-0229-2. 
    
    This function will choose n cells from batches, finds K nearest neighbors
    of each randomly chosen cell, and calculates the average regional entropy
    of all n cells. 
    
    The procedure is repeated for n_iter iterations. Finally, the average of the 
    iterations is returned as the final batch mixing score. 
    
    Parameters
    ----------
    latent_space : numpy ndarray 
        The latent space matrix.
        
    batches : a numpy array or a list
        The batch number of each sample in the latent space matrix.
        
    K : int
        Number of nearest neighbors. 
    
    n_jobs : int
        Number of jobs. Please visit scikit-learn documentation for more info. 
    
    n : int
        Number of cells to be chosen randomly. 
    
    n_iter : int
        Number of iterations to randomly choosing n cells.
    
    Returns
    -------
    L1 : float <= 1 
        The batch mixing score; the higher, the better.
    
    '''
    
    n_samples = latent_space.shape[0]
    nne = NearestNeighbors(n_neighbors=K+1, n_jobs=n_jobs)
    nne.fit(latent_space)
    kmatrix = nne.kneighbors_graph(latent_space) - scipy.sparse.identity(n_samples)
    
    ind = np.random.choice(n_samples, size=n)
    inds = kmatrix[ind].nonzero()[1].reshape(n, K)
    
    score = 0
    
    for t in range(n_iter):
        score += np.mean([entropy(batches[inds[i]])\
                          for i in range(n)])
    score = score/n_iter
    
    return score


    
    
    
    
    