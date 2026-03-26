"""Worst Case Analysis Algorithms."""
import math


from policies import *
from routes import *


def headway_bounds(route: list[Stop], start_times: list[float], t_max: float = float('inf')) -> tuple[list[float], list[float]]:
    """Calculate upper and lower headway bounds for each stop along a route.

    .. warning::
       This function is not guaranteed to converge for any arbitrary route.  Consider setting the ```t_max``` argument.

    :param route: The route to analyze.
    :param start_times: The list of start times at stop 0 for all vehicles serving the route.
    :param t_max: Optional cutoff time for routes that terminate service within a given interval.
    """
    M = len(start_times)
    N = len(route)
    i = 1
    stop = route[i]
    l = 0 #TODO: See N. Prev. Vehicles
    htub = [-float('inf')] * N
    htlb = [float('inf')] * N
    carry_in = [None] * N
    converged = False
    departures = start_times
    while not converged and departures[-1] < t_max:
        # Arrivals at stop i
        arrivals = []
        arrivals.append(departures[0] + max(stop.tau))
        for j in range(1, M):
            tau = min(max(min(stop.tau), arrivals[j - 1] - departures[j]), max(stop.tau))
            arrivals.append(departures[j] + tau)

        # Departures from stop i+1
        l += (i + 1) // N
        i = (i + 1) % N
        departures = []
        stop = route[i]
        a_leader_next_max = departures[0] + sum([max(stop.tau) + max(stop.delta) for stop in route])
        policy_args = {
            't': arrivals[0],
            'n_prev_veh': j + l * M,
            'd_leader': carry_in[i],
            'a_follower': departures[1] + max(stop.tau) if M > 1 else a_leader_next_max,
        }
        departures.append(arrivals[0] + max(max(stop.delta), stop.policy.get_hold_time(**policy_args)))
        for j in range(1, M):
            a_leader_nxt_min = departures[0] + sum([min(stop.tau) + min(stop.delta) for stop in route])
            policy_args = {
                't': arrivals[j],
                'n_prev_veh': j + l * M,
                'd_leader': departures[j - 1],
                'a_follower': departures[j + 1] + min(stop.tau) if j + 1 < M else a_leader_nxt_min,
            }
            delta = min(max(min(stop.delta), departures[j - 1] - arrivals[j]), max(stop.delta))
            departures.append(arrivals[j] + max(delta, stop.policy.get_hold_time(**policy_args)))

        # Update headway bounds
        if carry_in[i] is not None:
            wcht[i] = max(wcht[i], max(0, arrivals[i][0] - carry_in[i]))
        for j in range(1, M):
            bcht[i] = min(bcht[i], max(0, arrivals[i][j] - departures[i][j-1]))
        arrivals[i] = []
        carry_in[i] = departures[i][-1]
        t = departures[i][-1]
                
    return wcht, bcht
