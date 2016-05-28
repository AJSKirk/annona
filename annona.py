import pulp
import numpy as np

class SupplyChain(object):
    def __init__(self, name, sense=pulp.LpMinimize):
        self.name = name
        self.network = {}
        self.prob = pulp.LpProblem(name, sense)
    def get_layers(self):
        return self.network.keys()
    def add_layer(self, layer):
        if layer in self.network:
            raise DuplicateLayerException
        self.network[layer] = []
    def connect_layers(self, fr, to, costs):
        """Use np.inf in costs to kill an arc"""
        #TODO: Test
        self.network[fr].append(to) 
        arcs = np.array([pulp.LpVariable("{}{}->{}{}".format(fr.name,i+1,to.name,j + 1),0,None)
            for i in range(costs.shape[0]) for j in range(costs.shape[1])])
        arcs = arcs.reshape(costs.shape)

        self.prob += self.prob.objective + np.sum(costs * arcs), 'Total Cost'
        fr.add_out_arcs(arcs)
        to.add_in_arcs(arcs)
    def _build_constraints(self):
        for layer in self.network.keys():
            for cons in layer.get_constraints():
                self.prob.addConstraint(cons)
    def _solve(self):
        if self.prob.status < 0:
            print("Problem could not be solved")
            return
        if self.prob.status == 0:
            print("Solving problem")
            self._build_constraints()
            self.prob.solve()
    def get_cost(self):
        self._solve()
        return pulp.value(self.prob.objective)

    def print_arc_value(self):
        self._solve()
        for var in self.prob.variables():
            print("{} = {}".format(var.name, var.varValue))

class ChainLayer(object):
    def __init__(self, name, constraints):
        self.name = name + '_'
        self.constraints = constraints
        self.size = len(constraints)
    def add_in_arcs(self, arcs):
        self.in_arcs = arcs
    def add_out_arcs(self, arcs):
        self.out_arcs = arcs
    def get_input_totals(self):
        return np.sum(self.in_arcs, 0)
    def get_output_totals(self):
        return np.sum(self.out_arcs, 1)

class SupplyLayer(ChainLayer):
    def get_constraints(self):
        if len(self.get_output_totals()) != self.size:
            raise DimensionMismatchException
        return (pulp.LpConstraint(self.get_output_totals()[i],sense=-1,
            rhs=cons, name = self.name + str(i + 1))
            for i, cons in enumerate(self.constraints))

class DemandLayer(ChainLayer):
    def get_constraints(self):
        if len(self.get_input_totals()) != self.size:
            raise DimensionMismatchException
        return (pulp.LpConstraint(self.get_input_totals()[i],sense=1,
            rhs=cons, name = self.name + str(i + 1))
            for i, cons in enumerate(self.constraints))

class TransshipmentLayer(ChainLayer):
    def __init__(self, name):
        self.name = name + '_'
    def get_constraints(self):
        if len(self.get_input_totals()) != len(self.get_output_totals()):
            raise DimensionMismatchException
        return (pulp.LpConstraint(self.get_input_totals()[i] - self.get_output_totals()[i],
                sense=0, rhs=0, name = self.name + str(i + 1))
                for i in range(len(self.get_input_totals())))
