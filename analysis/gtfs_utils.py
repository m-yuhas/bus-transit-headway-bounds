"""Utilities to load a gtfs and populate travel and dwell times."""
from collections import defaultdict
from dataclasses import dataclass
from math import exp, log, sqrt
from os import path


from pandas import read_csv
from scipy.special import erfinv


from .routes import *


@dataclass
class GtfsStopConfig(StopConfig):
    """Configuration information required to construct a ```Stop``` with additional information appearing in a GTFS.

    :param stop_id: The stop_id as per the GTFS.
    :param arrival_rate: The number of passengers per minute arriving at stop.
    :param mean_dwell: The mean dwell time at the stop.
    :param mean_travel: The mean travel time leaving the stop.
    :param travel_var: The variance in travel time leaving the stop.
    """ 
    stop_id: str
    arrival_rate: float
    mean_dwell: float
    mean_travel: float
    travel_var: float


def get_quantile_log_normal(mu: float, sigma: float, q: float) -> float:
    """Get a quantile's upper boundary (x | p(X < x) = q) for a log-normal distribution parameterized by mu and sigma.

    :param mu: The distribution's logarithm of location.
    :param sigma: The distribution's logarithm of scale.
    :return: The quantile's upper bound.
    """
    return exp(mu + sqrt(2 * sigma ** 2) * erfinv(2 * q - 1))


def get_log_normal_mixture(mu: list[float], sigma: list[float], weights: list[float] | None = None) -> tuple[float]:
    """Get the parameters of a log normal mixture approximated by log normal distribution.
    
    :param mu: List of logarithms of location for every log-normal distribution in the mixture.
    :param sigma: List of logarithms of scale for every log-normal distribution in the mixture.
    :param weight: List of weights for each log-normal distribution in the mixture.
    """
    assert len(mu) == len(sigma)
    if weights is None:
        w = [1 / len(mu) for _ in range(len(mu))]
    else:
        assert len(weights) == len(mu)
        w = weights

    # Calculate moments
    m1 = 0
    m2 = 0
    for i in range(len(mu)):
        m1 += w[i] * exp(mu[i] + (sigma[i] ** 2) / 2)
        m2 += (w[i] ** 2) * exp(2 * mu[i] + 2 * sigma[i] ** 2)
    temp = 0
    for i in range(len(sigma)):
        for j in range(i+1,len(sigma)):
            temp += (w[i] * w[j]) * exp(mu[i] + mu[j] + 0.5 * (sigma[i] ** 2 + sigma[j] ** 2))
    m2 = m2 + 2 * temp

    # Calculate new parameters
    sigma = sqrt(log(m2/(m1 ** 2)))
    mu = log(m1) - (sigma ** 2) / 2
    return mu, sigma


def load_route_from_gtfs(route_id: int, service_day: str) -> tuple[list[GtfsStopConfig], list[float]]:
    """Create a route template from a GTFS.

    .. note ::
        This function makes some assumptions about the structure of routes in the GTFS.  For example we assume that earliest departure
        along a route starts in direction "1", not "0".

    :param route_id: The route id in the GTFS.
    :param service_day: The service day in the GTFS the route template will be based on.
    :returns: List of stop configurations in order of service and list of vehicle start times for the dominant blocks.
    :raises ValueError:
    """
    calendar = read_csv(path.join('gtfs', 'calendar.txt'))
    trips = read_csv(path.join('gtfs', 'trips.txt'))
    stops = read_csv(path.join('gtfs', 'stops.txt'))
    stop_times = read_csv(path.join('gtfs', 'stop_times.txt'))

    # Get service_id for selected day
    active_service_ids = calendar[calendar[service_day] == 1].service_id
    if len(active_service_ids) == 0:
        raise ValueError(f'No service on {service_day} in GTFS!')
    elif len(active_service_ids) > 1:
        raise ValueError(f'Multiple services on {service_day} in GTFS: multiple services are currently not supported!')
    service_id = active_service_ids.iloc[0]

    # Get the trips we care about
    trips = trips[(trips.service_id == service_id) & (trips.route_id == route_id)]

    # Map patterns (unique sequences of stops) to trips
    patterns_by_direction_id = defaultdict(set)
    trips_by_pattern = defaultdict(set)
    for block_id in [int(b) for b in trips.block_id.unique()]:
        for trip_id in [int(t) for t in trips[trips.block_id == block_id].trip_id.unique()]:
            pattern = tuple(stop_times[stop_times.trip_id == trip_id].sort_values(by='stop_sequence').stop_id)
            patterns_by_direction_id[trips[trips.trip_id == trip_id].direction_id.iloc[0].item()].add(pattern)
            trips_by_pattern[pattern].add(trip_id)

    # Select the most common pattern for each direction ID (we're ignoring weird, one-off patterns)
    selected_pattern_by_direction_id = {}
    for direction_id, patterns in patterns_by_direction_id.items():
        selected_pattern = max(patterns, key=lambda pattern: len(trips_by_pattern[pattern]))
        selected_pattern_by_direction_id[direction_id] = selected_pattern

    # Map stop_id and direction_id to Stop objects
    # Note: we assume direction_id=1, is the starting leg of the route
    stop_info = []
    for direction_id in list(selected_pattern_by_direction_id.keys())[::-1]:
        # Last stop in pattern is duplicated, since it is the first stop in the next direction
        for stop_id in selected_pattern_by_direction_id[direction_id][:-1]:
            stop_info.append(GtfsStopConfig(
                tau=None,
                delta=None,
                policy=BolehPolicy,
                policy_args={},
                stop_id=stop_id,
                arrival_rate=None,
                mean_dwell=None,
                mean_travel=None,
                travel_var=None,
            ))

    # Get scheduled departures for each stop
    scheduled_departures_by_stop_id = defaultdict(list)
    block_start_times: dict[float] = {}
    for pattern in selected_pattern_by_direction_id.values():
        for trip_id in trips_by_pattern[pattern]:
            stop_ids = tuple(stop_times[stop_times.trip_id == trip_id].sort_values(by='stop_sequence').stop_id)
            departure_times = tuple(stop_times[stop_times.trip_id == trip_id].sort_values(by='stop_sequence').departure_time)
            departure_times = tuple(d.strip().split(':') for d in departure_times)
            departure_times = tuple(int(h) * 60 + int(m) + int(s) / 60 for h, m, s in departure_times)
            for stop_id, departure_time in zip(stop_ids[:-1], departure_times[:-1]):
                scheduled_departures_by_stop_id[stop_id].append(departure_time)
            block_id = trips[trips.trip_id == trip_id].block_id.iloc[0].item()
            if block_id in block_start_times:
                block_start_times[block_id] = min(departure_times[0], block_start_times[block_id])
            else:
                block_start_times[block_id] = block_id
    for stop_id, scheduled_departures in scheduled_departures_by_stop_id.items():
        scheduled_departures.sort()

    # Get starting times
    block_start_times = sorted(list(block_start_times.values()))

    # Normalize all times so that the first block starts at t=0
    offset = block_start_times[0]
    for idx, time in enumerate(block_start_times):
        block_start_times[idx] -= offset
        # For some reason some blocks randomly start in the afternoon.
        # This messes up our metrics since we can't calculate headway until all the initial vehicles have departed.
        if block_start_times[idx] >= 200:
            block_start_times = block_start_times[:idx]
            break
    for departure_times in scheduled_departures_by_stop_id.values():
        for idx, _ in enumerate(departure_times):
            departure_times[idx] -= offset

    # Add departure times to each stop config
    for stop in stop_info:
        stop.scheduled_departures = scheduled_departures_by_stop_id[stop.stop_id]

    # Remove start times from first stop's scheduled departures
    for start_time in block_start_times:
        stop_info[0].scheduled_departures.remove(start_time)
    
    return stop_info, block_start_times


def load_times(route: list[GtfsStopConfig], service_day: str, lower_quantile: float, upper_quantile: float) -> list[GtfsStopConfig]:
    """Load the travel and dwell times for a route defined in the GTFS.

    .. warning ::
        This function modifies the route argument in addition to returning a route.
    
    :param route: List of stop configuration in order of stops.
    :param service_day: The day of the weak whose data will be used to calculate the parameters.
    :param lower_quantile: The lower quantile of observed travel and dwell times to consider.
    :param upper_quantile: The uppler quantile of observed travel and dwell times to consider.
    :return: The route with updated travel and dwell time bounds.
    """
    travel_times = read_csv(path.join('data', 'travel_times.csv'))
    alight_rates = read_csv(path.join('data', 'alight_rates.csv'))
    demand_rates = read_csv(path.join('data', 'demand_rates.csv'))

    for stop in route:
        tt = travel_times[(travel_times.day_of_week == service_day) & (travel_times.from_stop_id == stop.stop_id)]
        tt_mu = list(tt.mean_log_travel_time_s)
        tt_sigma = list(tt.std_log_travel_time_s)
        mu, sigma = get_log_normal_mixture(tt_mu, tt_sigma)
        lower = get_quantile_log_normal(mu, sigma, lower_quantile) / 60
        upper = get_quantile_log_normal(mu, sigma, upper_quantile) / 60
        stop.tau = (lower, upper)
        stop.mean_travel = get_quantile_log_normal(mu, sigma, 0.5) / 60
        stop.travel_var = exp(sigma ** 2 - 1) * exp(2 * mu + sigma ** 2)

        ar = alight_rates[alight_rates.STOP_ID == stop.stop_id]
        ar = list(ar.ALIGHT_RATE)
        dr = demand_rates[demand_rates.STOP_ID == stop.stop_id]
        dr = list(dr.HOURLY_DEMAND)
        stop.arrival_rate = sum(dr) / (len(dr) * 60)

        weights = []
        for a, d in zip(ar, dr):
            weights.extend([10 / len(ar), 2 * a / len(ar), 3.5 * d / len(dr)])
        mu, sigma = get_log_normal_mixture([0 for _ in range(len(weights))], [0.1 for _ in range(len(weights))], weights)
        lower = get_quantile_log_normal(mu, sigma, lower_quantile) / 60
        upper = get_quantile_log_normal(mu, sigma, upper_quantile) / 60
        stop.delta = (lower, upper)
        stop.mean_dwell = get_quantile_log_normal(mu, sigma, 0.5) / 60

    return route