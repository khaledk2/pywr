


class GraphInterface:
    def __init__(self, obj):
        self.obj = obj

    @property
    def graph(self):
        return self.obj.model.component_graph

    def add(self, item):
        if not isinstance(item, Component):
            return
        if self is self.obj.children:
            self.graph.add_edge(item, self.obj)
        else:
            self.graph.add_edge(self.obj, item)

    def remove(self, item):
        if not isinstance(item, Component):
            return
        if self is self.obj.children:
            self.graph.remove_edge(item, self.obj)
        else:
            self.graph.remove_edge(self.obj, item)

    def clear(self):
        for n in self._members:
            if self is self.obj.children:
                self.graph.remove_edge(n, self.obj)
            else:
                self.graph.remove_edge(self.obj, n)

    @property
    def _members(self):
        if self is self.obj.children:
            return [n for n in self.graph.predecessors(self.obj) if n != "root"]
        else:
            return self.graph.successors(self.obj)

    def __len__(self):
        """Returns the number of nodes in the model"""
        return len(self._members)

    def __iter__(self):
        return iter(self._members)




cdef class Component:
    """ Components of a Model

    This is the base class for all the elements of a `pywr.Model`,
     except the the nodes, that require updates via the `setup`, `reset`,
     `before`, `after` and `finish` methods. This class handles
     registering the instances on the `Model.component_graph` and
     managing the parent/children interface.

    The parent/children interface, through the `Model.component_graph`
     is used to create a dependency tree such that the methods are
     called in the correct order. E.g. that a `before` method in
     one component that is a parent of another is called first.

    See also
    --------
    `Model`

    """
    def __init__(self, model, name=None, comment=None):
        self._model = model
        self._name = name
        self.comment = comment
        model.component_graph.add_edge("root", self)
        self.parents = GraphInterface(self)
        self.children = GraphInterface(self)

    property name:
        def __get__(self):
            return self._name
        def __set__(self, value):
            self._name = value

    cpdef setup(self):
        pass

    cpdef reset(self):
        pass

    cpdef before(self):
        pass

    cpdef after(self):
        pass

    cpdef finish(self):
        pass

    property model:
        def __get__(self, ):
            return self._model