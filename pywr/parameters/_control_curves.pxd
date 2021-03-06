from .._core cimport Timestep, Scenario, ScenarioIndex, AbstractNode, Storage, AbstractStorage
from ._parameters cimport Parameter, IndexParameter

cdef class BaseControlCurveParameter(Parameter):
    cdef AbstractStorage _storage_node
    cdef list _control_curves

cdef class ControlCurveInterpolatedParameter(BaseControlCurveParameter):
    cdef double[:] _values

cdef class ControlCurveIndexParameter(IndexParameter):
    cdef public AbstractStorage storage_node
    cdef list _control_curves
