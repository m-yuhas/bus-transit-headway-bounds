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
        hold_time = max(0.0, self.schedule[self.idx] - t)
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
        """
        t = kwargs['t']
        hold_time = max(0.0, self.next_release - t)
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

class SlackDrivenPolicy(BasePolicy):
    """Hold buses based on slack time and stop control efficiency coefficient.

    This policy is based on:
    ```
    @article{liu_improving_2018,
        author  = {Liu, Shuozhi and Luo, Xia and Jin, Peter J.},
        title   = {Improving Bus Operations through Integrated Dynamic Holding Control and Schedule Optimization},
        journal = {Journal of Advanced Transportation},
        volume  = {2018},
        number  = {1},
        pages   = {9714046},
        year    = {2018},
        doi     = {10.1155/2018/9714046},
    }
    ```

    :param headway: The scheduled headway between buses.
    :param scheduled_slack: Scheduled slack time in minutes.
    :param efficiency_coefficient: Efficiency coefficient 'f' for this stop.
    :param beta: The demand rate at this stop.
    """
    def __init__(self, headway: float, scheduled_slack: float, efficiency_coefficient: float, beta: float) -> None:
        self.H = headway
        self.d = scheduled_slack
        self.f = efficiency_coefficient
        self.beta = beta
        self.t_curr = None
        self.t_prev = None
        self.a_prev = None

    def get_hold_time(self, **kwargs: dict[str, Any]) -> float:
        """Determine holding time given the bus's arrival time.
        
        :keyword t: The current time.
        :return: Holding time.
        """
        a_curr = kwargs['t']
        if self.t_curr is None:
            self.t_curr = a_curr
            self.a_prev = a_curr
            return 0
        else:
            self.t_prev = self.t_curr
            self.t_curr += self.H
        eps_curr = a_curr - self.t_curr
        eps_prev = self.a_prev - self.t_prev
        self.a_prev = a_curr
        return max(0, self.d - (1 + self.beta) * eps_curr + self.beta * eps_prev + self.f * eps_curr)
