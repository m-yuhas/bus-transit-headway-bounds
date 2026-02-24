"""Holding policies for bus routes."""
from typing import Dict, List, Tuple


class BasePolicy(object):
    """Base class for policies.  Every policy must inherit from this class."""

    def __init__(self) -> None:
        pass

    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        """Calculate holding time given some information.

        the keys in kwargs depend on the specific policy.
        """
        pass


class BolehPolicy(BasePolicy):
    """Never let a bus idle."""

    def __init__(self) -> None:
        pass

    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        return 0


class ScheduleDrivenPolicy(BasePolicy):
    """Dispatch buses based on a schedule.

    - A schedule is a list of times from t=0.
    - The list must extend to at least t_max.
    - This policy is designed to handle the case
     where the schedule changes depending on time
     of day, e.g., buses are dispatched more frequently
     during rush hour than off-peak hours.
    """

    def __init__(self, schedule: List[float]) -> None:
        self.schedule = schedule
        self.idx = 0
        
    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        """kwargs:
        t - time of this bus's arrival at the stop.
        """
        t = kwargs['t']
        if t >= self.schedule[self.idx]:
            hold_time = 0
        else:
            hold_time = self.schedule[self.idx] - t
        self.idx = (self.idx + 1) % len(self.schedule)
        return hold_time


class LeakyBucketPolicy(BasePolicy):
    """Dispatch buses based on schedule with constant dt.
    
    - This schedule policy is designed to handle the case
      where release times are constant throughout the day.
    - No list is needed, so it does not depend on t_max.
    - Acts as a leaky bucket, releasing vehicles at a constant
      rate, if they are present.
    """

    def __init__(self, time_delta: float, offset: float) -> None:
        """Schedule is a list of time."""
        self.time_delta = time_delta
        self.next_release = offset
    
    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        """kwargs:
        t - time of this bus's arrival at the stop.
        n_prev_veh - used only in DP mode to determine how many other vehicles have passed through
        """
        t = kwargs['t']
        if 'n_prev_veh' in kwargs:
            return max(0, self.time_delta * kwargs['n_prev_veh'] - t)
        if t >= self.next_release:
            hold_time = 0
        else:
            hold_time = self.next_release - t
        self.next_release += self.time_delta
        return hold_time


class RatioDrivenPolicy(BasePolicy):
    """Dispatch buses based on ideal headway/tailway ratio.
    
    Args:
        target_ratio - the target headway/tailway ratio on the output
        activation_ratio - incoming headway/tailway ratio needs to fall below this to activate the delay
        max_holding - do not hold vehicles longer than this amount
    """

    def __init__(self, target_ratio: float, activation_ratio: float, max_holding: float) -> None:
        self.target_ratio = target_ratio
        self.activation_ratio = activation_ratio
        self.max_holding = max_holding

    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        """kwargs:
        t - time of this bus's arrival at the stop.
        d_leader - departure of this bus's leader from the same stop.
        a_follower - estimated arrival time of this bus's follower.
        """
        d_leader = kwargs['d_leader']
        a_follower = kwargs['a_follower']
        a_self = kwargs['t']
        if d_leader is None or a_follower is None:
            return 0
        headway = a_self - d_leader
        tailway = a_follower - a_self
        if tailway == 0:
            return 0
        if headway / tailway < self.activation_ratio:
            d_self = a_follower - (1 / self.target_ratio) * (a_self - d_leader)
            return min(max(0, d_self - a_self), self.max_holding)
        else:
            return 0


class HeadwayDrivenPolicy(BasePolicy):
    """Dispatch buses to preserve constant headway.
    
    Args:
        target_headway - the target headway when leaving the stop.
    """

    def __init__(self, target_headway: float) -> None:
        self.target_headway = target_headway

    def get_hold_time(self, **kwargs: Dict[str, float]) -> float:
        """kwargs:
        t - time of this bus's arrival at the stop.
        d_leader - departure of this bus's leader from the same stop.
        """
        d_leader = kwargs['d_leader']
        a_self = kwargs['t']
        if d_leader is None:
            return 0
        headway = a_self - d_leader
        if headway < self.target_headway:
            return self.target_headway - headway
        else:
            return 0