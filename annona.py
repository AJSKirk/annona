from pulp import *
import numpy as np

def shipment(costs, smax, dmax):
    prob = LpProblem("Shipment", LpMinimize)
    x = np.array([LpVariable('x' + str(i) + str(j), 0, None)
         for i in range(costs.shape[0]) for j in range(costs.shape[1])])
    x = x.reshape(costs.shape)
    prob += np.sum(costs * x), 'Total Cost'
    
    for i in range(len(smax)):
        prob += np.sum(x[i]) <= smax[i], "Supply Constraint " + str(i)
    for i in range(len(dmax)):
        prob += np.sum(x.T[i]) >= dmax[i], "Demand " + str(i)
    return prob
    
def transshipment(costs_to, costs_from, smax, dmax):
    prob = LpProblem("Transshipment", LpMinimize)
    x_to = np.array([LpVariable('xt' + str(i) + str(j), 0, None)
         for i in range(costs_to.shape[0]) for j in range(costs_to.shape[1])])
    x_to = x_to.reshape(costs_to.shape)
    x_from = np.array([LpVariable('xf' + str(i) + str(j), 0, None)
         for i in range(costs_from.shape[0]) for j in range(costs_from.shape[1])])
    x_from = x_from.reshape(costs_from.shape)
    prob += np.sum(costs_to * x_to) + np.sum(costs_from * x_from), 'Total Cost'
    
    for i in range(len(smax)):
        prob += np.sum(x_to[i]) <= smax[i], "Supply Constraint " + str(i)
    for i in range(len(dmax)):
        prob += np.sum(x_from.T[i]) >= dmax[i], "Demand " + str(i)
    for i in range(int(costs_to.shape[1])):
        prob += np.sum(x_to.T[i]) - np.sum(x_from[i]) == 0, "Trans " + str(i)
        
    return prob
    
ct = np.array(
    [[7.33, 6.59],
    [9.29, 8.87],
    [9.11, 5.41]])
    
cf = np.array(
    [[3.49, 9.41, 8.81],
    [4.63, 8.77, 8.63]])

smax = [83, 127, 179]
dmax = [130, 129, 130]

z = transshipment(ct, cf, smax, dmax)