import pulp
import numpy as np

def WeightedAvgDist(dist, xs, total_demand, max_dist=None, thresh=None):
    return pulp.LpConstraint(np.sum(dist * arcs) / total_demand, sense=-1,
            rhs=thresh)

def PctInDist(dists, xs, total_demand, max_dist, thresh=None):
    return pulp.LpConstraint(((dists <= max_dist) * xs) / total_demand,
            sense=1, rhs=thresh)
