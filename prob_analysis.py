"""Probabilistic Route Analysis."""
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

import itertools
import random
import statistics

from policies import *
from routes import *


class VehicleState(Enum):
    DWELL = 0
    IDLE = 1
    TRAVEL = 2


@dataclass
class Vehicle:
    stop: Stop
    state: VehicleState
    next_state_timer: float
    policy_holding: float
    travel_times: List[float]
    last_departure: List[float]


def simulate(route: List[Stop], start_times: List[float], t_max: float, seed: int):
    """Probabilistic Simulation."""
    random.seed(seed)
    N = len(route)
    M = len(start_times)

    # Results Storage
    headway_times = [[] for _ in range(N)]
    travel_times = [[[] for _ in range(N)] for _ in range(N)]
    
    # Initialize Vehicle Positions
    vehicles = [Vehicle(
        stop=0,
        state=VehicleState.IDLE,
        next_state_timer=start_times[i],
        policy_holding=0,
        travel_times=[[0 for _ in range(N)] for _ in range(N)],
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
   
        # Update vehicles
        for idx, v in enumerate(vehicles):
            
            # Update travel times
            for x, y in itertools.product(list(range(N)), list(range(N))):
                v.travel_times[x][y] += dt

            # Update state
            if v.state == VehicleState.TRAVEL:
                v.next_state_timer -= dt
                if v.next_state_timer <= 0:
                    v.state = VehicleState.DWELL
                    v.stop = (v.stop + 1) % N
                    v.next_state_timer = random.uniform(*route[v.stop].delta)
                    for start_stop in range(N):
                        travel_times[start_stop][v.stop].append(v.travel_times[start_stop][v.stop])
                    for end_stop in range(N):
                        v.travel_times[v.stop][end_stop] = 0

                    next_arr_est = t
                    if vehicles[idx - 1].stop != v.stop:
                        if vehicles[idx - 1].state == VehicleState.DWELL:
                            next_arr_est += statistics.mean(route[vehicles[idx - 1].stop].delta)
                        next_arr_est += statistics.mean(route[vehicles[idx - 1].stop].tau)
                        s = (vehicles[idx - 1].stop + 1) % N
                        while s != v.stop:
                            next_arr_est += (statistics.mean(route[s].delta) + statistics.mean(route[s].tau))
                            s = (s + 1) % N
                    policy_args = {
                        't': t,
                        'd_leader': vehicles[(idx + 1) % M].last_departure[v.stop],
                        'a_follower': next_arr_est,
                    }
                    v.policy_holding = route[v.stop].policy.get_hold_time(**policy_args)
                    v.last_departure[v.stop] = t + max(v.next_state_timer, v.policy_holding)
                    route[v.stop].vehicles.append(v)

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
            else:
                raise Exception(f'Invalid state for vehicle {v}')

        # Calculate headway
        for idx, stop in enumerate(route):
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
        #print(f'Sim Time: {t}; dt: {dt}')

    return {'headway': headway_times, 'travel': travel_times}