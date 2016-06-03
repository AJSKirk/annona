import pulp
import numpy as np

def WeightedAvgDist(demand):
    return np.sum(demand.get_dist() * demand.get_arcs()) / demand.total_demand()

def PctInDist(demand, max_dist):
    return np.sum((demand.get_dist() <= max_dist) * demand.get_in_arcs()) / demand.total_demand()
