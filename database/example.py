from write_into_database import StreamType, collect_db, main
import pybgpstream
import datautils
from datetime import datetime
import time


timestamp = 1649169046
script_start_time = datautils.get_utc_time_scoop(timestamp, 30)[1]
time_to_wait = script_start_time - int(time.time())
if time_to_wait > 0:
    print(f'Program will start {int(time_to_wait/60)} minutes later...')
    time.sleep(time_to_wait)


stream_type = StreamType.UPDATE
prefix = "184.164.236.0/24"
_, mycol = collect_db(stream_type=stream_type, prefix=prefix)
time_scoop = datautils.get_utc_time_scoop(timestamp, 20)
print(f'start time: {datetime.utcfromtimestamp(time_scoop[0]).strftime("%Y-%m-%d %H:%M:%S")}')
print(f'end time: {datetime.utcfromtimestamp(time_scoop[1]).strftime("%Y-%m-%d %H:%M:%S")}')


stream = pybgpstream.BGPStream(
    from_time=time_scoop[0], until_time=time_scoop[1],
    record_type=stream_type.value,
    filter="prefix exact " + prefix
)

main(mycol=mycol, stream_type=stream_type, stream=stream)