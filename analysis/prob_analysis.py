"""Probabilistic Route Analysis."""
from dataclasses import dataclass
from enum import Enum


import itertools
import random
import statistics


from .policies import *
from .routes import *


class VehicleState(Enum):
    """A vehicle can be:
    - INItializing, i.e., it hasn't yet departed its initial stop;
    - DWELLing, i.e., waiting at a stop for passengers to embark and alight;
    - IDLE, i.e., waiting at a stop doing nothing;
    - TRAVELing, i.e., moving from one stop to the next.
    """
    INIT = -1
    DWELL = 0
    IDLE = 1
    TRAVEL = 2


@dataclass
class Vehicle:
    """A vehicle serving a bus route.

    :param stop: The vehicle's current stop.
    :param state: The vehicle's current state within a stop.
    :param next_state_timer: Time remaining until the vehicle's state is updated.
    :param policy_holding: Hold time calculated for the vehicle by a stop's policy.
    :param last_departure: List of times the vehicle last departed each stop.
    :param travel_times: Matrix of travel times with dim 0 indicating the origin stop and dim 1 indicating the destination stop.
    """
    stop: Stop
    state: VehicleState
    next_state_timer: float
    policy_holding: float
    last_departure: list[float | None]
    travel_times: list[list[float | None]]


def get_policy_args(route: list[Stop], vehicles: list[Vehicle], t: float, veh_idx: int) -> dict[str, Any]:
    """Get the arguments to supply to a holding policy given the current vehicle positions in route.

    .. important:: This function must not modify any data in route or vehicles.
    .. note:: This function assumes that the vehicle list is ordered by position along the route.

    :param route: The route being simulated.
    :param vehicles: List of vehicles serving the route.
    :param t: The current simulation time.
    :param veh_idx: The index of the vehicle for which the hold time will be calculated.
    """
    N = len(route)
    M = len(vehicles)
    next_arr_est = t
    if vehicles[veh_idx - 1].stop != vehicles[veh_idx].stop:
        if vehicles[veh_idx - 1].state == VehicleState.DWELL:
            next_arr_est += statistics.mean(route[vehicles[veh_idx - 1].stop].tau)
            s = (vehicles[veh_idx - 1].stop + 1) % N
            while s != vehicles[veh_idx].stop:
                next_arr_est += (statistics.mean(route[s].delta) + statistics.mean(route[s].tau))
                s = (s + 1) % N
    return {
        't': t,
        'd_leader': vehicles[(veh_idx + 1) % M].last_departure[vehicles[veh_idx].stop],
        'a_follower': next_arr_est,
    }


def simulate(route: list[Stop], start_times: list[float], t_max: float, seed: int = 0) -> dict[str, list]:
    """Simulate a bus route and collect headway times at each stop and travel times between every stop pair.
    
    :param route: The route to analyze.
    :param start_times: The list of start times at stop 0 for all vehicles serving the route.
    :param t_max: Simulation cutoff time.
    :param seed: Seed value for random number generator.
    """
    random.seed(seed)
    N = len(route)
    M = len(start_times)

    # Results Storage
    headway_times = [[] for _ in range(N)]
    travel_times = [[[] for _ in range(N)] for _ in range(N)]
    
    # Initialize Vehicle Positions
    vehicles = [Vehicle(
        stop=0,
        state=VehicleState.INIT,
        next_state_timer=start_times[i],
        policy_holding=0,
        travel_times=[[None for _ in range(N)] for _ in range(N)],
        last_departure=[None for _ in range(N)]) for i in range(M)
    ]

    # Initialize Wait Time at Each Stop
    for stop in route:
        stop.wait_time = None
        
    # Main Loop
    t = 0
    dt = 0
    while t <= t_max:

        # Tick
        t += dt

        # Arrange vehicles by completion order along the route
        vehicles = sorted(vehicles, key=lambda x: (x.stop, x.state.value, -x.next_state_timer))

        # Get vehicles currently held at each stop
        for idx, stop in enumerate(route):
            stop.vehicles = [v for v in vehicles if v.stop == idx and (v.state == VehicleState.DWELL or v.state == VehicleState.IDLE)]
            stop.init_list = [v for v in vehicles if v.stop == idx and v.state == VehicleState.INIT]
    
        # Update vehicles
        for idx, v in enumerate(vehicles):
            
            # Update travel times
            for x, y in itertools.product(list(range(N)), list(range(N))):
                if v.travel_times[x][y] is not None and len(route[0].init_list) == 0:
                    v.travel_times[x][y] += dt

            # Update state
            if v.state == VehicleState.TRAVEL:
                v.next_state_timer -= dt
                if v.next_state_timer <= 0:
                    v.state = VehicleState.DWELL
                    v.stop = (v.stop + 1) % N
                    v.next_state_timer = random.uniform(*route[v.stop].delta)
                    for start_stop in range(N):
                        if start_stop == v.stop:
                            # TODO: Do we care about travel time back to the same stop?
                            # For now I'm assuming we ignore this case
                            travel_times[start_stop][v.stop].append(0)
                        elif v.travel_times[start_stop][v.stop] is not None:
                            travel_times[start_stop][v.stop].append(v.travel_times[start_stop][v.stop])
                    for end_stop in range(N):
                        v.travel_times[v.stop][end_stop] = 0
                    v.policy_holding = route[v.stop].policy.get_hold_time(**get_policy_args(route, vehicles, t, idx))
                    v.last_departure[v.stop] = t + max(v.next_state_timer, v.policy_holding)
            elif v.state == VehicleState.DWELL:
                v.next_state_timer -= dt
                v.policy_holding -= dt
                if v.next_state_timer <= 0:
                    v.state = VehicleState.IDLE
                    v.next_state_timer = max(0, v.policy_holding)
            elif v.state == VehicleState.IDLE:
                v.policy_holding = 0
                v.next_state_timer -= dt
                if v.next_state_timer <= 0:
                    v.state = VehicleState.TRAVEL
                    v.next_state_timer = random.uniform(*route[v.stop].tau)
                    v.last_departure[v.stop] = t
            elif v.state == VehicleState.INIT:
                v.next_state_timer -= dt
                if v.next_state_timer <= 0:
                    v.state = VehicleState.IDLE
                    v.policy_holding = route[v.stop].policy.get_hold_time(**get_policy_args(route, vehicles, t, idx))
                    v.last_departure[v.stop] = t + max(v.next_state_timer, v.policy_holding)
                    route[v.stop].vehicles.append(v)
            else:
                raise Exception(f'Invalid state for vehicle {v}')
        
        # Calculate headway
        for idx, stop in enumerate(route):
            if len(stop.init_list) > 0:
                continue
            if stop.wait_time is not None and len(stop.vehicles) == 0:
                stop.wait_time += dt
            for v in stop.vehicles:
                if v.state == VehicleState.DWELL and stop.wait_time is not None:
                    headway_times[idx].append(stop.wait_time)
                    stop.wait_time = None
                    break
                elif v.state == VehicleState.IDLE:
                    stop.wait_time = 0

        # Update clock
        dt = min([v.next_state_timer for v in vehicles])

    return {'headway': headway_times, 'travel': travel_times}
