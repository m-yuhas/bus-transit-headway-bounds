# Historical Travel and Dwell Time Data Format
In order to generate the data distributions for travel and dwell time at each stop, the data files in the following sections are required.
The column values are explained in the respective sections.

Dwell times are assumed to be proportional to the number of alighting and boarding passengers, where the time it takes each passenger to alight or board is given by a log-normal distribution.
We use the approximation that the sum of random variables drawn from log-normal distributions is itself log-normally distributed, and use the method of moments to calculate the dwell time distribution whose quantiles we use to get the dwell time bounds for a given stop.

Travel times are assumed to be lognormally distributed and we take the weighted average of estimated travel time ditributions at each hour of the selected day (also log-normally distributed), from which we calculate the quantiles to get the travel time bounds for a given stop.

## alight_rates.csv
* **STOP_ID** - The stop_id from the GTFS for which the alight rate is being calculated.  This should be unique.
* **ROUTE_DIRECTION_NAME** - As long as the stop_ids are unique, this will be ignored.
* **HOUR** - The hour of the day for which the alight rate is valid.
* **ALIGHT_RATE** - The average number of passengers alighting a bus at the specified STOP_ID at the specified HOUR.  This is not the global alight rate for the entire hour, but the average alight rate for each bus that arrives in the one-hour interval starting at HOUR.

## demand_rates.csv
* **STOP_ID** - The stop_id from the GTFS for which the alight rate is being calculated.  This should be unique.
* **ROUTE_DIRECTION_NAME** - As long as the stop_ids are unique, this will be ignored.
* **HOUR** - The hour of the day for which the alight rate is valid.
* **HOURLY_DEMAND** - The average number of passengers boarding a bus at the specified STOP_ID at the specified HOUR.  This is not the global hourly demand, but the average number of passengers boarding each bus that arrives in the on-hour interval starting at HOUR.

## travel_times.csv
* **directionId** - As long as the stop_ids are unique, this will be ignored.
* **from_stop_id** - The stop_id in the GTFS from which travel begins.
* **to_stop_id** - The stop_id in the GTFS at which travel ends.
* **day_of_week** - The day of week for which the distribution is valid.
* **hour_of_day** - The hour of the day_of_week for which the distribution is valid.
* **mean_log_travel_time_s** - The logarithm of location parameter for the log normal distribution modeling travel time between from_stop_id and to_stop_id given in seconds.
* **std_log_travel_time_s** - The logarithm of scale parameter for the log normal distribution modeling travel time between from_stop_id and to_stop_id given in seconds.
