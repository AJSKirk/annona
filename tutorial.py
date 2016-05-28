# Start by importing the annona module
from annona.chain import *

# Create a supply chain. The chain is where all of our optimisation happens
sc = SupplyChain('SteelCo')

# Create the supply layer, specifying the maximum output from each DC
supply = SupplyLayer('Distribution Centre', [100000, 100000])

# The DemandLayer is similar to the SupplyLayer object, but creates constraints
# around minimum input to each demand sure
demand = DemandLayer('Contractor Site', [40500, 22230, 85200, 47500])

# The cost matrix is a numpy array, specifying the costs for arcs between an
# outgoing layer (i.e. a factory) and an incoming layer (i.e. a consumer facing
# store). The outgoing nodes correspond to rows, the incoming nodes to columns

# In this case, we have 2 supply nodes and 4 demand nodes, so costs is a 2x4
# matrix
costs = np.array([
    [52, 32, 11, 69],
    [45, 84, 76, 15]])

# Note that we need to explicitly attach our layers to the chain before
# conencting them
sc.add_layer(supply)
sc.add_layer(demand)

# Now, we draw the arcs from suppy to demand, weighted according to costs
# If two particular nodes can not be connected, assign that cell np.inf in the
# costs matrix
sc.connect_layers(supply, demand, costs)

# Calling get_cost() will automatically invoke the simplex solver
print sc.get_cost()

# We can also have the chain print out the values of each decision variable
sc.print_arc_values()

## In our second example, we show an example of transshipment in annona

sc2 = SupplyChain('RCH Industries')
supply = SupplyLayer('Factory', [200, 300, 100, 150, 220])

# The Transshipment layer takes an argument for the maximum throughput at each
# transshipment site. In this case, there are no limits on the throughput of
# each crossdock, so we specify None for both.

# Note that all transshipment layers must clear, so their total inputs and
# total outputs must perfectly cancel
trans = TransshipmentLayer('Crossdock', [None, None])
cost_to_crossdock = np.array([
    [30, 50],
    [23, 66],
    [35, 14],
    [70, 12],
    [65, 70]])

demand = DemandLayer('Regional DC', [150, 100, 110, 200, 180])
cost_to_dc = np.array([
    [12, 25, 22, 40, 41],
    [65, 22, 23, 12, 15]])

sc2.add_layer(supply)
sc2.add_layer(trans)
sc2.connect_layers(supply, trans, cost_to_crossdock)
sc2.add_layer(demand)
sc2.connect_layers(trans, demand, cost_to_dc)

print sc2.get_cost()
sc2.print_arc_values()
