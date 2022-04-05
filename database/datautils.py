from datetime import datetime
from time import time

def get_utc_time_scoop(utc_timestamp, minute_interval):
    '''
    This function is to get a utc time scoop given a timestamp.
    Example:
        input:
            utc_timestamp = 1649154828 # (2022-04-05 10:33:48 UTC)
            minute_interval = 20
        output:
            (1649154600, 1649155800)
            # (2022-04-05 10:30:00 UTC, 2022-04-05 10:50:00 UTC)
    '''
    time_left = int(utc_timestamp / 600) * 600
    time_right = time_left + 60 * minute_interval
    return (time_left, time_right)