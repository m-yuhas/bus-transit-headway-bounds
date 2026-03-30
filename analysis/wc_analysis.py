"""Worst Case Analysis Algorithms."""
import math


from .policies import *
from .routes import *


def headway_bounds(route: list[Stop], start_times: list[float], t_max: float = float('inf')) -> tuple[list[float], list[float]]:
    """Calculate upper and lower headway bounds for each stop along a route.

    .. warning::
        This function is not guaranteed to converge for any arbitrary route.  Consider setting the ```t_max``` argument.
    .. note::
        In the paper, we over write the vectors of arrivals and departures every time the loop index advances, but some policies may require
        information about all the past vehicle locations.  Instead, we use M x N matrices to track the past arrivals and departures at each stop,
        which does not affect the memory complexity, although it deviates slightly from the algorithm presented in the paper.

    :param route: The route to analyze.
    :param start_times: The list of start times at stop 0 for all vehicles serving the route.
    :param t_max: Optional cutoff time for routes that terminate service within a given interval.
    """
    M = len(start_times)
    N = len(route)
    i = 0
    stop = route[i]
    htub = [-float('inf')] * N
    htlb = [float('inf')] * N
    carry_in = [None] * N
    arrivals = [[] for _ in range(N)]
    departures = [[] for _ in range(N)]
    departures[0] = start_times
    converged = False
    while not converged and departures[i][-1] < t_max:
        # Update index
        i_prev = i
        i = (i + 1) % N
        stop_prev = stop
        stop = route[i]

        # Calculate Arrivals
        arrivals[i] = []
        arrivals[i].append(departures[i_prev][0] + max(stop_prev.tau))
        for j in range(1, M):
            tau = min(max(min(stop_prev.tau), arrivals[i][j - 1] - departures[i_prev][j]), max(stop_prev.tau))
            arrivals[i].append(departures[i_prev][j] + tau)

        # Calculate Departures
        departures[i] = []
        policy_args = {
            't': arrivals[i][0],
            'd_leader': carry_in[i],
            'a_follower': (departures[i_prev][1] + max(stop_prev.tau) if M > 1
                           else departures[i_prev][0] + sum([max(stop.tau) + max(stop.delta) for stop in route])
            ),
        }
        departures[i].append(arrivals[i][0] + max(max(stop.delta), stop.policy.get_hold_time(**policy_args)))
        for j in range(1, M):
            policy_args = {
                't': arrivals[i][j],
                'd_leader': departures[i][j - 1],
                'a_follower': (departures[i_prev][j + 1] + min(stop_prev.tau) if j + 1 < M
                               else departures[i][0] + sum([min(stop.tau) + min(stop.delta) for stop in route])
                ),
            }
            delta = min(max(min(stop.delta), departures[i][j - 1] - arrivals[i][j]), max(stop.delta))
            departures[i].append(arrivals[i][j] + max(delta, stop.policy.get_hold_time(**policy_args)))

        # Calculate worst case headway
        if carry_in[i] is not None:
            if max(0, arrivals[i][0] - carry_in[i]) > htub[i]:
                htub[i] = max(0, arrivals[i][0] - carry_in[i])
            else:
                converged = True
        if max(0, arrivals[i][1] - departures[i][0]) < htlb[i]:
            htlb[i] = max(0, arrivals[i][1] - departures[i][0])
            coverged = False
        carry_in[i] = departures[i][-1]
                
    return htub, htlb
