from ._recorders import Recorder
from pywr.parameters import Parameter, IndexParameter
import numpy as np
import pandas


class Event(object):
    """ Container for event information """
    def __init__(self, start, scenario_index):
        self.start = start
        self.scenario_index = scenario_index
        self.end = None

    @property
    def duration(self):
        td = self.end.datetime - self.start.datetime
        return td.days


class EventRecorder(Recorder):
    """Track discrete events using a Parameter or Recorder

    The recorder works with an `IndexParameter`, `Parameter` or `Recorder`. An
    event is considered active while the value of the threshold is non-zero.

    The events are stored in a flat list across all scenarios. Each
    event is stored as a separate `Event` object. Events can be accessed as a
    dataframe using the `to_dataframe` method.

    Parameters
    ----------
    threshold - IndexParameter, Parameter or Recorder
       The object that defines the start and end of an event.
    minimum_event_lenght - int (default=1)
        The minimum number of time-steps that an event must last for
        to be recorded. This is useful to not record events that are
        caused by model hysteresis. The default will cause all events
        to be recorded.

     See also
     --------
     `pywr.parameters._thresholds`


     """
    def __init__(self, model, threshold, minimum_event_length=1, **kwargs):
        super(EventRecorder, self).__init__(model, **kwargs)
        self.threshold = threshold
        self.threshold.parents.add(self)
        if minimum_event_length < 1:
            raise ValueError('Keyword "minimum_event_length" must be >= 1')
        self.minimum_event_length = minimum_event_length
        self.events = None
        self._current_events = None

    def setup(self):
        pass

    def reset(self):
        self.events = []
        # This list stores if an event is current active in each scenario.
        self._current_events = [None for si in self.model.scenarios.combinations]

    def after(self):
        # Current timestep
        ts = self.model.timestepper.current

        if isinstance(self.threshold, Recorder):
            all_triggered = np.array(self.threshold.values(), dtype=np.int)
        elif isinstance(self.threshold, IndexParameter):
            all_triggered = self.threshold.get_all_indices()
        elif isinstance(self.threshold, Parameter):
            all_triggered = np.array(self.threshold.get_all_values(), dtype=np.int)
        else:
            raise TypeError("Threshold must be either a Recorder or Parameter instance.")

        for si in self.model.scenarios.combinations:
            # Determine if an event is active this time-step/scenario combination
            triggered = all_triggered[si.global_id]

            # Get the current event
            current_event = self._current_events[si.global_id]
            if current_event is not None:
                # A current event is active
                if triggered:
                    # Current event continues
                    pass
                else:
                    # Update the end of the current event.
                    current_event.end = ts
                    current_length = ts.index - current_event.start.index

                    if current_length >= self.minimum_event_length:
                        # Current event ends
                        self.events.append(current_event)
                        # Event has ended; no further updates
                        current_event = None
                    else:
                        # Event wasn't long enough; don't append
                        current_event = None
            else:
                # No current event
                if triggered:
                    # Start of a new event
                    current_event = Event(ts, si)
                else:
                    # No event active and one hasn't started
                    # Therefore do nothing.
                    pass

            # Update list of current events
            self._current_events[si.global_id] = current_event

    def finish(self):
        ts = self.model.timestepper.current
        # Complete any unfinished events
        for si in self.model.scenarios.combinations:
            # Get the current event
            current_event = self._current_events[si.global_id]
            if current_event is not None:
                # Unfinished event
                current_event.end = ts
                self.events.append(current_event)
                self._current_events[si.global_id] = None

    def to_dataframe(self):
        """ Returns a DataFrame containing all of the events. """
        # Return empty dataframe if no events are found.
        if len(self.events) == 0:
            return pandas.DataFrame(columns=['scenario_id', 'start', 'end'])

        scen_id = np.empty(len(self.events), dtype=np.int)
        start = np.empty_like(scen_id, dtype=object)
        end = np.empty_like(scen_id, dtype=object)

        for i, evt in enumerate(self.events):
            scen_id[i] = evt.scenario_index.global_id
            start[i] = evt.start.datetime
            end[i] = evt.end.datetime

        return pandas.DataFrame({'scenario_id': scen_id, 'start': start, 'end': end})


class EventDurationRecorder(Recorder):
    """ Recorder for the duration of events found by an EventRecorder

    This Recorder uses the results of an EventRecorder to calculate the duration
    of those events in each scenario. Aggregation by scenario is done via
    the pandas.DataFrame.groupby() method.

    Any scenario which has no events will contain a NaN value.

    Parameters
    ----------
    event_recorder : EventRecorder
        EventRecorder instance to calculate the events.

    """
    def __init__(self, model, event_recorder, **kwargs):
        # Optional different method for aggregating across self.recorders scenarios
        agg_func = kwargs.pop('recorder_agg_func', kwargs.get('agg_func'))
        self.recorder_agg_func = agg_func

        super(EventDurationRecorder, self).__init__(model, **kwargs)
        self.event_recorder = event_recorder
        self.event_recorder.parents.add(self)

    def setup(self):
        self._values = np.empty(len(self.model.scenarios.combinations))

    def reset(self):
        self._values[...] = 0.0

    def after(self):
        pass

    def values(self):
        return self._values

    def finish(self):
        df = self.event_recorder.to_dataframe()

        self._values[...] = 0.0
        # No events found
        if len(df) == 0:
            return

        # Calculate duration
        df['duration'] = df['end'] - df['start']
        # Convert to int of days
        df['duration'] = df['duration'].dt.days
        # Drop other columns
        df = df[['scenario_id', 'duration']]

        # Group by scenario ...
        grouped = df.groupby('scenario_id').agg(self.recorder_agg_func)
        # ... and update the internal values
        for index, row in grouped.iterrows():
            self._values[index] = row['duration']
