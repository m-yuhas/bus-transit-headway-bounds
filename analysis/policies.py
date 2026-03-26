"""Holding policies for bus routes."""
from typing import Any


class BasePolicy(object):
    """Base class for holding policies.
    
    The constructor may take any number of arbitrary arguments.

    :raises NotImplementedError:
    """

    def __init__(self) -> None:
        raise NotImplementedError('BasePolicy is an abstract class, do not use this for scheduling!')

    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Compute policy holding time.

        This method must accept a dictionary of kwargs, even though it does not have to use all of them.  The entries in kwargs represent the sytem
        state at the point a holding time needs to be computed.  The required args should be enumerated in the docstring.  The return value must be
        a positive real number (inclusive of 0.0) in floating point representation, which corresponds to the amount of time to hold a vehicle given
        the state.

        :return: Holding time.
        :raises NotImplementedError:
        """
        raise NotImplementedError('BasePolicy is an abstract class, do not use this for scheduling!')


class BolehPolicy(BasePolicy):
    """Never hold a bus."""

    def __init__(self) -> None:
        pass

    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Holding time is always 0.0, regardless of system state.

        :return: 0.0
        """
        return 0.0


class ScheduleDrivenPolicy(BasePolicy):
    """Dispatch buses based on a static schedule.

    This class handles the case where a schedule contains a finite number of release times (e.g., a route operating for one day).  If you need a
    schedule that schedule that releases vehicles on regular intervals in perpetuity, consider using ```InfiniteSchedulePolicy```.
    
    :param schedule: List of scheduled departure times.
    """

    def __init__(self, schedule: list[float]) -> None:
        self.schedule = schedule
        self.idx = 0
        
    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Hold a bus only if it arrives before the next scheduled departure.
        
        :keyword t: The current time.
        :return: Holding time.
        """
        t = kwargs['t']
        if t >= self.schedule[self.idx]:
            hold_time = 0.0
        else:
            hold_time = self.schedule[self.idx] - t
        self.idx = (self.idx + 1) % len(self.schedule)
        return hold_time


class InfiniteSchedulePolicy(BasePolicy):
    """Dispatches buses on a periodic schedule in perpetuity.

    This class only handles a schedule with regular intervals.  If you need a schedule with aperiodic release times (e.g., running buses at
    different frequencies depending on time of day), consider using ```ScehduleDrivenPolicy```.
    
    :param time_delta: Time between scheduled releases.
    :param offset: Schedule phase.
    """

    def __init__(self, time_delta: float, offset: float) -> None:
        self.time_delta = time_delta
        self.next_release = offset
    
    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Hold a bus only if it arrives before the next scheduled departure.
        
        :keyword t: The current time.
        :return: Holding time.

        # TODO: See if n_prev_veh is still need for DP
        """
        t = kwargs['t']
        if 'n_prev_veh' in kwargs:
            return max(0.0, self.time_delta * kwargs['n_prev_veh'] - t)
        if t >= self.next_release:
            hold_time = 0.0
        else:
            hold_time = self.next_release - t
        self.next_release += self.time_delta
        return hold_time


class HeadwayDrivenPolicy(BasePolicy):
    """Hold buses to maximize the headway/tailway ratio.

    This policy is based on the one described in:
    ```
    @article{zhou2022,
        author = {Chang Zhou and Qiong Tian and David Z.W. Wang},
        doi = {10.1016/j.tranpol.2022.04.022},
        journal = {Transport Policy},
        month = jul,
        pages = {1-13},
        title = {A novel control strategy in mitigating bus bunching: Utilizing real-time information},
        volume = {123},
        year = {2022},
    }
    ```

    :param activation_ratio: Do not issue holding time unless the headway/tailway ratio falls below this value.
    :param max_holding: Do not hold vehicles longer than this interval.
    """

    def __init__(self, activation_ratio: float, max_holding: float) -> None:
        self.activation_ratio = activation_ratio
        self.max_holding = max_holding

    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Hold a bus until headway == tailway.
        
        :keyword t: The current time.
        :keyword d_leader: The departure time of the lead vehicle.
        :keyword a_follower: The estimated arrival time of the following vehicle.
        :return: Holding time.
        """
        d_leader = kwargs['d_leader']
        a_follower = kwargs['a_follower']
        a_self = kwargs['t']
        if d_leader is None or a_follower is None:
            return 0.0
        headway = a_self - d_leader
        tailway = a_follower - a_self
        if tailway == 0:
            return 0.0
        elif headway / tailway < self.activation_ratio:
            return min(max(0, (a_follower + d_leader - 2 * a_self) / 2), self.max_holding)
        else:
            return 0.0
