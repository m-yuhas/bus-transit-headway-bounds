"""Route Creation."""
from typing import Any, TypedDict
from dataclasses import dataclass


from policies import *


@dataclass
class Stop(object):
    """A stop in a bus route.

    :param tau: Tuple containing the minimum and maximum travel time to the next stop.
    :param delta: Tuple containing the minimum and maximum dwell time at this stop.
    :param policy: The holding policy governing this stop.
    """
    tau: tuple[float, float]
    delta: tuple[float, float]
    policy: BasePolicy


class StopConfig(TypedDict):
    """Dictionary containing the required information to construct a ```Stop```.
    
    .. note::
        Used only for type hints.
    
    :param tau: Tuple containing the minimum and maximum travel time to the next stop.
    :param delta: Tuple containing the minimum and maximum dwell time at this stop.
    :param policy: The holding policy governing this stop.
    :param policy_args: kwargs provided to the policy constructor.
    """ 
    tau: tuple[float, float]
    delta: tuple[float, float]
    policy: BasePolicy
    policy_args: dict[str, Any]


def route_factory(config: list[StopConfig]) -> list[Stop]:
    """Create a new instance of a route from a template.

    A route is a list of ```Stops```.  Because the policies at stops are stateful, they must be recreated when starting a new simulation; this is
    the route factory's job.

    :param config: List of configurations for each stop in the route.
    :return: A new instance of a route.
    """
    route = []
    for stop in config:
        route.append(Stop(
            tau=stop['tau'],
            delta=stop['delta'],
            policy=stop['policy'](**stop['policy_args']),
        ))
    return route
