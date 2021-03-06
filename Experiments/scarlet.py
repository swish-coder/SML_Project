"""Scarlet_Paper.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1sHLZ0VCI9hcJ4IvWHR1fYNejrlF3URft
"""

import copy
import numpy as np
from numpy.linalg import norm
from Experiments.sampling_from_gaussian import generate_psd_cov_mat
from utils import plot_error_vs_samples
np.random.seed((3,14159))

def normalize_data(B,v_max,lamda,X_samples,Y_samples):
  norm_const = 1/((B)*np.sqrt(v_max*(lamda + 1)))
  normed_X = X_samples.copy()
  normed_Y = Y_samples.copy()
  for sample in range(Y_samples.shape[0]):
    normed_X[sample] = norm_const*X_samples[sample]
    normed_Y[sample] = norm_const*Y_samples[sample]
  return normed_X,normed_Y

def find_max_lambda(cov_mat):
  num_nodes = cov_mat.shape[0]
  lamdas = []
  for _node1 in range(num_nodes):
    lamda_i = 0
    for _node2 in range(_node1+1,num_nodes):
      lamda_i += cov_mat[_node1,_node2]
    lamda_i/=cov_mat[_node1,_node1]
    lamdas.append(abs(lamda_i))

  return max(lamdas)

def generate_normed_samples(T, mean, cov_mat, lamda):
  num_nodes = cov_mat.shape[0]
  T_samples = np.random.multivariate_normal(mean, cov_mat,T)
  delta = 0.5
  B = np.sqrt(2 * np.log((2*num_nodes*T)/delta))
  var_mat = cov_mat.diagonal()
  v_max = np.max(var_mat)
  X_samples = []
  Y_samples = []
  for idx in range(num_nodes):
    Y_samples.append(T_samples[:,idx])
    _sample = T_samples.copy()
    _sample = np.delete(_sample, np.s_[idx], axis=1)
    X_samples.append(_sample)

  X_samples = np.asarray(X_samples)
  X_samples = np.swapaxes(X_samples,0,1)
  Y_samples = np.asarray(Y_samples)
  Y_samples = np.swapaxes(Y_samples,0,1)
  # lambda_i is < lambda(known-value)  where i \in [number of nodes].
  normed_X, normed_Y = normalize_data(B,v_max, lamda, X_samples, Y_samples)

  return normed_X, normed_Y

def test_sparsitron(normed_X_T,normed_Y_T,normed_X_M,normed_Y_M,lamda,beta):
  T = normed_X_T.shape[0]
  M = normed_X_M.shape[0]
  orig_attr = normed_X_T.shape[1]
  num_attr = 2*orig_attr+1
  w_t = 1/num_attr * np.ones([1,num_attr])
  w_arr = []
  p_arr = []
  emp_risk = []
  for t in range(T):
    x_t = normed_X_T[t,:]
    x_t = np.hstack([x_t,-x_t])
    x_t = np.hstack([x_t,0])
    y_t = normed_Y_T[t]
    w_arr.append(w_t)
    p_arr.append(w_t/norm(w_t,1))
    lamda_pt_xt = lamda*p_arr[t].dot(x_t)
    _loss = (1/2)*(1+(lamda_pt_xt-y_t)*(x_t))
    for i in range(num_attr):
      w_t[0][i]=w_t[0][i]*(beta**_loss[i])

  w_arr = np.asarray(w_arr)
  w_arr = w_arr[:,0,:orig_attr]-w_arr[:,0,orig_attr:-1]
  p_arr = np.asarray(p_arr)
  p_arr = p_arr[:,0,:orig_attr]-p_arr[:,0,orig_attr:-1]
  # normed_X_M = np.hstack([normed_X_M,-normed_X_M])
  # normed_X_M = np.hstack([normed_X_M,0])
  for t in range(T):
    pred = lamda*p_arr[t].dot(normed_X_M.T)
    emp_risk.append(np.sum((pred-normed_Y_M)**2)/M)
  return w_arr[emp_risk.index(min(emp_risk))], lamda*p_arr[emp_risk.index(min(emp_risk))]

def get_min_norm_edge(min_non_norm_wts):
  # Each var is divided by (var(i)*var(j))^(1/2).
  # Apply row-wise op followed by column-wise op. For, numpy computational efficiency.
  diag = np.diag(min_non_norm_wts)**0.5 # Pre-computing the root and also rounding at the end, to avoid floating point errors.
  
  for row in range(min_non_norm_wts.shape[0]):
    min_non_norm_wts[row] = min_non_norm_wts[row]/(diag[row])
  for col in range(min_non_norm_wts.shape[1]):
    min_non_norm_wts[col] = min_non_norm_wts[col]/(diag[col])

  min_non_norm_wts = np.round(min_non_norm_wts,5)
  assert np.all(np.diag(min_non_norm_wts)==np.ones(min_non_norm_wts.shape[0]))

  return np.min(min_non_norm_wts)

def test_error(sup_prec_mat, true_adj_mat):
  # print('Zeros in learnt adj mat: ',np.count_nonzero(sup_prec_mat==0))
  # print('Correctly predicted: ',np.count_nonzero(sup_prec_mat==true_adj_mat))
  # print('False positives: ',len(np.where(sup_prec_mat==1 & sup_prec_mat!=true_adj_mat)))
  # print('False negatives: ',len(np.where(sup_prec_mat==0 & sup_prec_mat!=true_adj_mat)))
  size = sup_prec_mat.shape[0]**2
  error = (size-np.count_nonzero(sup_prec_mat==true_adj_mat))/size
  return error

def compute_thresholded_sup_prec_mat(min_non_norm_wts):
  num_nodes = min_non_norm_wts.shape[0]
  node_deg = np.unique(np.nonzero(min_non_norm_wts)[0],return_counts=True)
  max_deg_d = max(node_deg[1])
  min_norm_edge = get_min_norm_edge(min_non_norm_wts)
  edge_condition = 2*min_norm_edge/3

  sup_prec_mat = [[0]*num_nodes]*num_nodes
  for node_i in range(num_nodes-1):
    for node_j in range(node_i,num_nodes-1):
      # print(max(min_non_norm_wts[node_i][node_j],min_non_norm_wts[node_j][node_i]),edge_condition)
      if max(min_non_norm_wts[node_i][node_j],min_non_norm_wts[node_j][node_i])>edge_condition: # min_wts or min_non_norm_wts?
        # print('Condition satisfied.')
        sup_prec_mat[node_i][node_j+1]=1
        sup_prec_mat[node_j+1][node_i]=1

  sup_prec_mat = np.asarray(sup_prec_mat)

  return sup_prec_mat

""" 
From Lemma 2 in the Paper:
First we have X = (x_1,...,x_p) and a inv_cov_mat. X is zero-mean.
In addition to X and cov_mat, we also have -
T_samples = (X1,...,XT) that are independent and have the same distribution as X.
So T_samples ----> (x_t,y_t) need to be normalized and passed to Sparsitron.
"""
def exp_scarlet(candidate_num_nodes = [10,20,30],candidate_Ts = [100,500,1000]):
  for num_nodes in candidate_num_nodes:
    errors = []
    for T in candidate_Ts:
      num_obs = T
      M = int(T/4)
      num_attr = num_nodes-1
      beta = 1/(1+np.sqrt(np.log(num_attr)/T))   #beta is the update parameter

      true_adj_mat, cov_mat = generate_psd_cov_mat(num_nodes,num_obs,force=True)
      lamda = find_max_lambda(cov_mat)  # lambda is a reserved keyword in Python.

      mean = [0 for i in range(cov_mat.shape[0])]
      normed_X_T, normed_Y_T = generate_normed_samples(T, mean, cov_mat, lamda) # Dimensions : (samples,Y/nodes,X/nodes-1)
      normed_X_M, normed_Y_M = generate_normed_samples(M, mean, cov_mat, lamda)

      min_wts = []
      min_non_norm_wts = []
      num_attr = num_nodes-1

      # Run sparsitron and compute weights for all nodes. 
      for _node in range(num_nodes):
        non_norm_wts, norm_wts = test_sparsitron(normed_X_T[:,_node,:].reshape(T,num_attr),normed_Y_T[:,_node].reshape(T,1),normed_X_M[:,_node,:].reshape(M,num_attr),normed_Y_M[:,_node].reshape(M,1),lamda,beta)
        min_wts.append(norm_wts)
        non_norm_wts_list = list(non_norm_wts)
        non_norm_wts_list.insert(_node,np.var(normed_Y_T[:,_node]))
        min_non_norm_wts.append(non_norm_wts_list)

      min_wts = np.asarray(min_wts)
      min_non_norm_wts = np.asarray(min_non_norm_wts)

      sup_prec_mat = compute_thresholded_sup_prec_mat(min_non_norm_wts)
      
      errors.append(test_error(sup_prec_mat,true_adj_mat))
    plot_error_vs_samples('Scarlet',errors,candidate_Ts,num_nodes)
      
