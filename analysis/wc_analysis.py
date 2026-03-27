"""Worst Case Analysis Algorithms."""
import math


from .policies import *
from .routes import *


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

        # Update index
        l += (i + 1) // N
        i = (i + 1) % N
        old_departures = departures
        departures = []
        stop = route[i]

        # Departures from stop i+1
        policy_args = {
            't': arrivals[0],
            #'n_prev_veh': j + l * M,
            'd_leader': carry_in[i],
            'a_follower': (old_departures[1] + max(stop.tau) if M > 1
                           else old_departures[0] + sum([max(stop.tau) + max(stop.delta) for stop in route])
            ),
        }
        departures.append(arrivals[0] + max(max(stop.delta), stop.policy.get_hold_time(**policy_args)))
        for j in range(1, M):
            policy_args = {
                't': arrivals[j],
                #'n_prev_veh': j + l * M,
                'd_leader': departures[j - 1],
                'a_follower': (old_departures[j + 1] + min(stop.tau) if j + 1 < M
                               else old_departures[0] + sum([min(stop.tau) + min(stop.delta) for stop in route])
                ),
            }
            delta = min(max(min(stop.delta), departures[j - 1] - arrivals[j]), max(stop.delta))
            departures.append(arrivals[j] + max(delta, stop.policy.get_hold_time(**policy_args)))

        # Update headway bounds
        if carry_in[i] is not None:
            if max(0, arrivals[0] - carry_in[i]) > htub[i]:
                htub[i] = max(0, arrivals[0] - carry_in[i])
            else:
                converged = True
        if max(0, arrivals[1] - departures[0]) < htlb[i]:
            htlb[i] = max(0, arrivals[1] - departures[0])
            converged = False
        carry_in[i] = departures[-1]
                
    return htub, htlb
