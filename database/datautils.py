from copy import deepcopy
import json

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

class DataManager():
    def __init__(self):
        self._get_monitors()
        self._get_template()

    def _get_monitors(self):
        with open('../testbed/scripts/meta_configs/routeviews_mons.json', 'r') as f:
            self.routeviews_mons: list = json.load(f)

        with open('../testbed/scripts/meta_configs/ris_mons.json', 'r') as f:
            self.ris_mons: list = json.load(f)

        self.all_mons: list = self.routeviews_mons + self.ris_mons

    def _get_template(self):
        with open('./pipeline_template.json', 'r') as f:
            self.pipeline_template: dict = json.load(f)

    def aggregate_constructor(self, as_path_slice: list, monitors: list=None):
        if monitors is None:
            monitors = self.all_mons
        
        as_path_slice = [str(as_path) for as_path in as_path_slice]
        slice_len = len(as_path_slice)

        agg_pipelines = []

        for monitor in monitors:
            pipeline = deepcopy(self.pipeline_template)
            pipeline[1]["$match"]["collector"] = monitor
            pipeline[2]["$match"]["$expr"]["$eq"][0]["$slice"][1] -= slice_len
            pipeline[2]["$match"]["$expr"]["$eq"][1] += as_path_slice
            agg_pipelines.append(pipeline)
        
        return agg_pipelines