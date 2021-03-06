import pulp
import numpy as np

class SupplyChain(object):
    """Main Supply Chain class. All arcs and optimisation happens here."""
    def __init__(self, name, sense=pulp.LpMinimize):
        self.name = name
        self.network = {}
        self.prob_seed = pulp.LpProblem(name, sense)
        self.clean = True
        self.variables = {}

        self.fixed_costs = {}
        self.link_constraints = {}
        self.throughput_constraints = {}
        self.los_constraints = {}
    def get_layers(self):
        return self.network.keys()
    def add_layer(self, layer):
        """Attaches a layer to the supply chain. Made explicit to control when
        layers are changed."""
        if layer in self.network:
            print('WARNING: Layer {} already in this chain.' + 
            'Old layer has been overwritten'.format(layer.name))
        self.network[layer] = {}
        self.variables[layer] = {}
        layer._attach_to_chain(self)
        self.fixed_costs[layer] = layer.get_fixed_costs()
        self.clean = False
    def remove_layer(self, layer):
        try:
            del self.network[layer]
            del self.variables[layer]
            del self.fixed_costs[layer]
            for fr in self.network.values():
                if layer in fr:
                    del fr[layer]
            for fr in self.variables.values():
                if layer in fr:
                    del fr[layer]
        except KeyError:
            print('WARNING: Layer {} not in chain {}'.format(layer.name,
                self.name))
        self.clean = False
    def update_layer(self, layer):
        raise NotImplemented
    def connect_layers(self, fr, to, costs, dist=None):
        """Draws arcs between from and to layers. Automatically creates
        decision variables and updates the total cost for the chain. Use np.inf
        in the costs matrix to delete an arc. Note that layers must be
        explicitly attached to the chain beforehand."""
        if fr not in self.network:
            raise LayerNotAttachedException(fr, self)
        if to not in self.network:
            raise LayerNotAttachedException(to, self)
        arcs = [pulp.LpVariable("{}{}->{}{}".format(fr.name,i+1,to.name,j + 1),0,None)
            for i in range(costs.shape[0]) for j in range(costs.shape[1])]
        arcs = np.array(arcs).reshape(costs.shape)

        self.variables[fr][to] = arcs

        self.network[fr][to] = np.sum(costs * arcs)
        fr.add_out_arcs(arcs)
        to.add_in_arcs(arcs)
        to.add_dist(dist)
        self.clean = False
    def _build_constraints(self):
        for layer in self.network.keys():
            for cons in layer.get_constraints(): self.prob.addConstraint(cons)
            if layer.get_pmin_constraint(): self.prob.addConstraint(layer.get_pmin_constraint())
            if layer.get_pmax_constraint(): self.prob.addConstraint(layer.get_pmax_constraint())
            if layer.get_link_constraints():
                for cons in layer.get_link_constraints(): self.prob.addConstraint(cons)
            if layer.get_los_constraints():
                for cons in layer.get_los_constraints(): self.prob.addConstraint(cons)
    def _build_objective(self):
        for fr in self.network:
            for to in self.network[fr]:
                self.prob += self.prob.objective + self.network[fr][to]
        for layer in self.fixed_costs.values():
            self.prob += self.prob.objective + layer
    def _solve(self):
        if self.clean == False:
            self.prob = self.prob_seed.copy()
            #self.prob.addVariables(self.variables)
            print("Solving problem")
            self._build_constraints()
            self._build_objective()
            self.prob.solve()
            if self.prob.status < 0:
                print("Problem could not be solved")
                return
            self.clean = True
    def get_cost(self):
        self._solve()
        if self.prob.status < 0:
            return None
        return pulp.value(self.prob.objective)
    def get_arc_values(self):
        self._solve()
        if self.prob.status < 0:
            return None
        return dict([(var.name, var.varValue)
            for var in self.prob.variables])
    def print_arc_values(self):
        self._solve()
        if self.prob.status < 0:
            return None
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
        self.los_constraints = []
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
    def get_in_arcs(self):
        return self.in_arcs
    def add_dist(self, dist):
        if dist is None: return
        if dist.shape != self.in_arcs.shape:
            raise DimensionMismatchException
        self.dist = dist
    def get_dist(self):
        return self.dist
    def get_input_totals(self):
        return np.sum(self.in_arcs, 0)
    def get_output_totals(self):
        return np.sum(self.out_arcs, 1)
    def get_los_constraints(self):
        pass
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
            max(self.constraints[i], 10000000000000000) * self.ys[i],
            sense=-1, rhs = 0, name=self.name + '_link' + str(i)) for i in
            range(self.size)]
    def set_ys(self, new_ys):
        if not all(map(lambda x: x == 0 or x == 1, new_ys)):
            raise InvalidYsError
        if len(new_ys) != len(self.ys):
            raise InvalidYsError
        if sum(new_ys) > self.pmax or sum(new_ys) < self.pmin:
            raise InvalidYsError
        self.ys = new_ys
        self.chain.refresh_layer(self)
    def set_pmin(self, new_pmin):
        self.pmin = new_pmin
    def set_pmax(self, new_pmax):
        self.pmax = new_pmax




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
    def total_demand(self):
        return sum(self.constraints)
    def add_los_constraint(self, thresh, constraint_fn, *cons_args):
        # TODO: Make this better with some FP
        if constraint_fn.__name__ == 'PctInDist':
            sense = 1
        else:
            sense = -1
        self.los_constraints.append(pulp.LpConstraint(constraint_fn(self, *cons_args),
            sense=sense, rhs=thresh, name='{}_LOS_{}'.format(self.name,
                len(self.los_constraints))))
    #TODO: Make multi-naming work
    def los(self, constraint_fn, *cons_args):
        # TODO: Make this better with some FP
        print(pulp.value(constraint_fn(self, *cons_args)))
    def get_los_constraints(self):
        return self.los_constraints

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
                    sense=0, rhs=0, name = self.name + str(i + 1) +  '_Clear')
        for i, cons in enumerate(self.constraints):
            if cons:
                yield pulp.LpConstraint(self.get_input_totals()[i],sense=-1,
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
