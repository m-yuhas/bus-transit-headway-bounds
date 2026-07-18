"""Route Creation."""
from typing import Any
from dataclasses import dataclass


from .policies import *


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


@dataclass
class StopConfig(object):
    """Configuration information required to construct a ```Stop```.

    :param tau: Tuple containing the minimum and maximum travel time to the next stop.
    :param delta: Tuple containing the minimum and maximum dwell time at this stop.
    :param policy: The holding policy governing this stop.
    :param policy_args: kwargs provided to the policy constructor.
    """ 
    tau: tuple[float, float]
    delta: tuple[float, float]
    policy: BasePolicy
    policy_args: dict[str, Any]


@dataclass
class RouteConfig(object):
    """Configuration information that defines a route variant under test.
    
    :param name: Name used for identification.
    :param route: List of stops.
    :param start_times: List of times when vehicles start serving the route.
    """ 
    name: str
    route: list[Stop]
    start_times: list[float]


@dataclass
class HeadwayResults(object):
    """Headway experiment results.
    
    :param upper_bound: List of maximum possible headway at each stop.
    :param lower_bound: List of minimum possible headway at each stop.
    :param observed: List of headway times observed during simulation at each stop.
    """ 
    upper_bound: list[float]
    lower_bound: list[float]
    observed: list[list[float]]


@dataclass
class RouteResults(object):
    """Results from an experiment on one route variant.
    
    :param name: Name used for identification.
    :param route: The route under consideration.
    :param headway: Simulated and analytical headway results for the route.
    :param travel_time: Measured travel times between all pairs of stops.
    """ 
    name: str
    route: list[Stop]
    headway: HeadwayResults
    travel_time: list[list[list[float]]]


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
            tau=stop.tau,
            delta=stop.delta,
            policy=stop.policy(**stop.policy_args),
        ))
    return route
