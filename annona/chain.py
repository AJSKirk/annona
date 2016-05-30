import pulp
import numpy as np

class SupplyChain(object):
    """Main Supply Chain class. All arcs and optimisation happens here."""
    def __init__(self, name, sense=pulp.LpMinimize):
        self.name = name
        self.network = {}
        self.prob = pulp.LpProblem(name, sense)
        self.y_constraints = {}
        self.fixed_costs = {}
        self.link_constraints = {}
        self.throughput_constraints = {}
    def get_layers(self):
        return self.network.keys()
    def add_layer(self, layer):
        """Attaches a layer to the supply chain. Made explicit to control when
        layers are changed."""
        if layer in self.network:
            print('WARNING: Layer {} already in this chain.' + 
            'Old layer has been overwritten'.format(layer.name))
        self.network[layer.name] = {}
        layer._attach_to_chain(self)
        self.y_constraints[layer.name] = (layer.get_pmin_constraint(),
                layer.get_pmax_constraint())
        self.fixed_costs[layer.name] = layer.get_fixed_costs()
    def connect_layers(self, fr, to, costs):
        """Draws arcs between from and to layers. Automatically creates
        decision variables and updates the total cost for the chain. Use np.inf
        in the costs matrix to delete an arc. Note that layers must be
        explicitly attached to the chain beforehand."""
        if fr.name not in self.network:
            raise LayerNotAttachedException(fr, self)
        if to.name not in self.network:
            raise LayerNotAttachedException(to, self)
        arcs = [pulp.LpVariable("{}{}->{}{}".format(fr.name,i+1,to.name,j + 1),0,None)
            for i in range(costs.shape[0]) for j in range(costs.shape[1])]
        self.prob.addVariables(arcs)
        arcs = np.array(arcs).reshape(costs.shape)
        self.prob.addVariables

        self.network[fr.name][to.name] = np.sum(costs * arcs)
        fr.add_out_arcs(arcs)
        to.add_in_arcs(arcs)
        self.link_constraints[fr.name] = fr.get_link_constraints()
        self.throughput_constraints[fr.name] = fr.get_constraints()
        self.throughput_constraints[to.name] = to.get_constraints()
    def _build_constraints(self):
        for layer in self.throughput_constraints.values():
            for cons in layer:
                self.prob.addConstraint(cons)
        for layer in self.y_constraints.values():
            if layer[0] is not None: self.prob.addConstraint(layer[0])
            if layer[1] is not None: self.prob.addConstraint(layer[1])
        for layer in self.link_constraints.values():
            if layer is not None:
                for cons in layer:
                    if cons.name not in self.prob.constraints: self.prob.addConstraint(cons)
    def _build_objective(self):
        for fr in self.network:
            for to in self.network[fr]:
                self.prob += self.prob.objective + self.network[fr][to]
        for layer in self.fixed_costs.values():
            self.prob += self.prob.objective + layer
    def _solve(self):
        if self.prob.status < 0:
            print("Problem could not be solved")
            return
        if self.prob.status == 0:
            print("Solving problem")
            self._build_constraints()
            self._build_objective()
            self.prob.solve()
    def get_cost(self):
        self._solve()
        return pulp.value(self.prob.objective)
    def get_arc_values(self):
        return dict([(var.name, var.varValue)
            for var in self.prob.variables])
    def print_arc_values(self):
        self._solve()
        for var in self.prob.variables():
            print("{} = {}".format(var.name, var.varValue))
        
class ChainLayer(object):
    """Base class for supply chain layers"""
    def __init__(self, name, constraints, fixed_locs=True, pmin=0, pmax=None,
            fixed_costs=None):
        self.name = name + '_'
        self.constraints = constraints
        self.size = len(constraints)
        self.chain = None
        self.fixed_locs = fixed_locs
        if not fixed_locs:
            self.pmin = pmin
            self.pmax = pmax
            if self.pmax == None: self.pmax = self.size
            self.ys = np.array([pulp.LpVariable(self.name + '_Y' + str(i), 0,
                1, cat=pulp.LpBinary)
                for i in range(self.size)])
        else:
            self.ys = np.array([1] * self.size)
        if fixed_costs is None: fixed_costs = [0] * self.size
        self.fixed_costs = np.array(fixed_costs)
    def _attach_to_chain(self, chain):
        if self.chain:
            print('WARNING: This layer already in chain {}'.format(self.chain.name))
        self.chain = chain
    def add_in_arcs(self, arcs):
        self.in_arcs = arcs
    def add_out_arcs(self, arcs):
        self.out_arcs = arcs
    def get_input_totals(self):
        return np.sum(self.in_arcs, 0)
    def get_output_totals(self):
        return np.sum(self.out_arcs, 1)
    def get_pmin_constraint(self):
        if self.fixed_locs: return None
        return pulp.LpConstraint(np.sum(self.ys), sense=1, rhs=self.pmin,
                name=self.name+'_Pmin')
    def get_pmax_constraint(self):
        if self.fixed_locs: return None
        return pulp.LpConstraint(np.sum(self.ys), sense=-1, rhs=self.pmax,
                name=self.name+'_Pmax')
    def get_fixed_costs(self):
        return self.fixed_costs.dot(self.ys)
    def get_link_constraints(self):
        if self.fixed_locs: return None
        return [pulp.LpConstraint(self.get_output_totals()[i] - 
            self.constraints[i] * self.ys[i],
            sense=-1, rhs = 0, name=self.name + '_link' + str(i)) for i in
            range(self.size)]



class SupplyLayer(ChainLayer):
    """Supply layer. Takes a name and a list of constraints specifying the
    maximum output from each node in the layer"""
    def get_constraints(self):
        if len(self.get_output_totals()) != self.size:
            raise DimensionMismatchException(len(self.get_output_totals()), self.size)
        return (pulp.LpConstraint(self.get_output_totals()[i],sense=-1,
            rhs=cons, name = self.name + str(i + 1))
            for i, cons in enumerate(self.constraints))

class DemandLayer(ChainLayer):
    """Demand layer. Takes a name and a list of constraints specifying the
    minimum input for each node in the layer"""
    def get_constraints(self):
        if len(self.get_input_totals()) != self.size:
            raise DimensionMismatchException(len(self.get_input_totals()), self.size)
        return (pulp.LpConstraint(self.get_input_totals()[i],sense=1,
            rhs=cons, name = self.name + str(i + 1))
            for i, cons in enumerate(self.constraints))

class TransshipmentLayer(ChainLayer):
    """Transshipment layer. Takes a name and a list of constraints specifying
    the maximum throughput for each node in the layer. All nodes in a
    transshipment layer are required to have inputs and outputs balanced"""
    def get_constraints(self):
        if len(self.get_input_totals()) != len(self.get_output_totals()):
            raise DimensionMismatchException(
                    len(self.get_input_totals()), len(self.get_output_totals()))
        if len(self.get_input_totals()) != self.size:
            raise DimensionMismatchException(len(self.get_input_totals()), self.size)
        for i in range(self.size):
            yield pulp.LpConstraint(self.get_input_totals()[i] - self.get_output_totals()[i],
                    sense=0, rhs=0, name = self.name + str(i + 1))
        for i, cons in enumerate(self.constraints):
            if cons:
                yield pulp.LpConstraint(self.get_input_totals()[i],sense=1,
                    rhs=cons, name = self.name + str(i + 1))

class LayerNotAttachedException(Exception):
    def __init__(self, layer, chain):
        self.layer = layer
        self.chain = chain
    def __str__(self):
        return "ERROR: Layer {} not explicitly attached to Supply Chain {}".format(
                self.layer.name, self.chain.name)

class DimensionMismatchException(Exception):
    def __init__(self, d1, d2):
        self.d1 = d1
        self.d2 = d2
    def __str__(self):
        return "ERROR: Dimensions {} and {} do not match".format(
                self.d1, self.d2)
