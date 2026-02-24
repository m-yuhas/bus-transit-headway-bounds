"""Route Creation."""
from typing import Dict, List, Tuple, Union # TODO: switch to typed dict
from dataclasses import dataclass


from policies import *


@dataclass
class Stop(object):
    """A stop in a route is parameterized by:
    tau - minimum and maximum travel time to the next stop
    delta - minimum and maximum dwell time at this stop
    policy - policy governing additional holding at this stop.

    A route is a list of stops.
    """
    tau: Tuple[float, float]
    delta: Tuple[float, float]
    policy: BasePolicy


def route_factory(config: Dict[str, Union[Tuple, BasePolicy, Dict]]) -> List[Stop]:
    """Create new instances of routes from a template.
    The policies in routes are stateful and so need to be reset
    when starting a new simulation.
    """
    route = []
    for stop in config:
        route.append(Stop(
            tau=stop['tau'],
            delta=stop['delta'],
            policy=stop['policy'](**stop['policy_args']),
        ))
    return route