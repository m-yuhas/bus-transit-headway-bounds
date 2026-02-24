"""Worst Case Analysis Algorithms."""
from policies import *
from routes import *

def wcht(route: List[Stop], start_times: List[float], t_max: float) -> List[float]:
    """Calculate Worst Case Headway Times (WCHT) for a route.

    Args:
        route - list of stops
        start_times - time at which each bus is initially released from the first stop (regardless of holding policy)
        t_max - maximum time to consider
    """
    M = len(start_times)
    N = len(route)
    i = 0
    t = 0
    l = 0
    wcht = [0] * N
    carry_in = [None] * N
    arrivals = [[] for _ in range(N)]
    departures = [[] for _ in range(N)]
    departures[0] = start_times
    while t < t_max:
        # Update index
        l += (i + 1) // N
        i = (i + 1) % N
        stop = route[i]

        # Calculate Arrivals
        for j in range(M):
            if j == 0:
                arrivals[i].append(departures[(i - 1) % N][j] + max(stop.tau))
            else:
                tau = min(max(min(stop.tau), arrivals[i][j - 1] - departures[(i - 1) % N][j]), max(stop.tau))
                arrivals[i].append(departures[(i - 1) % N][j] + tau)
        #print(i, arrivals)
        arrivals[i].sort()

        # Calculate Departures
        for j in range(M):
            if j == 0:
                policy_args = {
                    't': arrivals[i][j],
                    'n_prev_veh': j + l * M,
                    'd_leader': carry_in[i],
                    'a_follower': departures[(i - 1) % N][j + 1] + max(stop.tau) # TODO: handle case with one vehicle
                }
                departures[i].append(arrivals[i][j] + max(max(stop.delta), stop.policy.get_hold_time(**policy_args)))
            else:
                a_leader_nxt_min = departures[i][0] + sum([min(stop.tau) + min(stop.delta) for stop in route])
                policy_args = {
                    't': arrivals[i][j],
                    'n_prev_veh': j + l * M,
                    'd_leader': departures[i][j - 1],
                    'a_follower': departures[(i - 1) % N][j + 1] + min(stop.tau) if j + 1 < M else a_leader_nxt_min
                }
                delta = min(max(min(stop.delta), departures[i][j - 1] - arrivals[i][j]), max(stop.delta))
                departures[i].append(arrivals[i][j] + max(delta, stop.policy.get_hold_time(**policy_args)))
        departures[(i - 1) % N] = []
        departures[i].sort()

        # Calculate worst case headway
        if carry_in[i] is not None:
            wcht[i] = max(wcht[i], arrivals[i][0] - carry_in[i])
        for j in range(1, M):
            if arrivals[i][j] > departures[i][j - 1]:
                wcht[i] = max(wcht[i], arrivals[i][j] - departures[i][j - 1])
        arrivals[i] = []
        carry_in[i] = departures[i][-1]
        t = departures[i][-1]
                
    return wcht


def wctt(route: List[Stop], start_times: List[float], wcht: List[float], start_stop: int, end_stop: int) -> float:
    """Calculate worst-case in-vehicle travel time."""
    N = len(route)
    M = len(start_times)
    idxs = []
    if start_stop == end_stop:
        return 0
    elif start_stop < end_stop:
        idxs = list(range(start_stop, end_stop))
    else:
        idxs = list(range(start_stop, N))
        idxs.extend(list(range(end_stop)))
    slowest = []
    fastest = []
    for i in idxs[::-1]:
        d_earliest = max(route[i].tau)
        d_latest = min(route[i].tau)

        if isinstance(route[i].policy, BolehPolicy):
            a_earliest = d_earliest + max(route[i].delta)
            a_latest = d_latest + min(route[i].delta)
        elif isinstance(route[i].policy, LeakyBucketPolicy):
            a_earliest = d_earliest + max(max(route[i].delta), route[i].policy.time_delta)
            a_latest = d_latest + min(route[i].delta)
        elif isinstance(route[i].policy, RatioDrivenPolicy):
            a_earliest = d_earliest + max(max(route[i].delta), route[i].policy.max_holding) #TODO:
            a_latest = d_latest + min(route[i].delta)
        elif isinstance(route[i].policy, HeadwayDrivenPolicy):
            a_earliest = d_earliest + max(max(route[i].delta), route[i].policy.target_headway) # TODO:
            a_latest = d_latest + min(route[i].delta)
        else:
            raise Exception(f"Policy {type(route[i].policy)} is not yet supported!")


    return d_earliest