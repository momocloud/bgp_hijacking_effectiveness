from copy import deepcopy
import enum
import json
from dataclasses import dataclass
from os import remove
from re import L
import pymongo


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
    
    def gen_dataset(self, as_path: list, col: pymongo.collection.Collection):
        return GenedDataSet(as_path, col, self)

    def remove_empty_monitors(self, datasets: list):
        empty_poses = list()
        empty_monitor_list = list()
        monitor_len = len(datasets[0].monitor_list)
        for dataset in datasets:
            dataset.monitor_list == monitor_len

        for mon_index in range(monitor_len):
            pop_needed = True
            for dataset in datasets:
                if dataset.victim_list[mon_index] != 0 or dataset.hijacker_list[mon_index] != 0:
                    pop_needed = False
                    break
            if pop_needed:
                empty_poses.append(mon_index)
        
        remove_ref = 0

        for pos in empty_poses:
            empty_monitor_list.append(datasets[0].monitor_list[pos - remove_ref])
            for dataset in datasets:
                dataset.monitor_list.pop(pos - remove_ref)
                dataset.victim_list.pop(pos - remove_ref)
                dataset.hijacker_list.pop(pos - remove_ref)
            remove_ref += 1

        return empty_monitor_list

    def intersect_peer_data(self, datasets: list):
        peer_sets = list()
        for dataset in datasets:
            dataset._init()
            dataset_peers_dic = {}
            for monitor, pairs in dataset.result_dict.items():
                dataset_peers_dic.update({monitor: {
                    'victim': set([peer['_id'] for peer in pairs['victim']]), 
                    'hijacker': set([peer['_id'] for peer in pairs['hijacker']]),
                    'both':
                    set([peer['_id'] for peer in pairs['victim']]) | 
                    set([peer['_id'] for peer in pairs['hijacker']])
                }
                })
            peer_sets.append(dataset_peers_dic)

        common_set = deepcopy(peer_sets[0])
        for monitor, sets in common_set.items():
            common_set[monitor] = sets['both']

        for peer_set in peer_sets:
            for monitor, peers in peer_set.items():
                common_set[monitor] = common_set[monitor] & peers['both']

        for peer_set in peer_sets:
            for monitor, peers in peer_set.items():
                peers['victim'] = peers['victim'] & common_set[monitor]
                peers['hijacker'] = peers['hijacker'] & common_set[monitor]

        for set_index, dataset in enumerate(datasets):
            dataset.victim_list = list()
            dataset.hijacker_list = list()
            peer_set = peer_sets[set_index]
            for peers in peer_set.values():
                dataset.victim_list.append(len(peers['victim']))
                dataset.hijacker_list.append(len(peers['hijacker']))
        

@dataclass
class GenedDataSet:
    as_path: list
    vic_pipelines: list
    hij_pipelines: list

    result_dict: dict
    col: pymongo.collection.Collection

    monitor_list: list
    victim_list: list
    hijacker_list: list

    def __init__(self, as_path, col, data_manager: DataManager) -> None:
        self.result_dict = {}
        self.monitor_list = []
        self.victim_list = []
        self.hijacker_list = []
        self.as_path = as_path
        self.victim_asn = as_path[-1]
        self.col = col
        self.vic_pipelines = data_manager.aggregate_constructor([as_path[-1]])
        self.hij_pipelines = data_manager.aggregate_constructor(as_path)
        self._init()

    def _init(self):
        self.monitor_list = []
        self.victim_list = []
        self.hijacker_list = []        

        for pipeline in self.vic_pipelines:
            monitor = pipeline[1]["$match"]["collector"]
            self.result_dict.setdefault(monitor, {})
            self.result_dict[monitor].setdefault("victim", [])
            self.result_dict[monitor]["victim"] = list(self.col.aggregate(pipeline))

        for pipeline in self.hij_pipelines:
            monitor = pipeline[1]["$match"]["collector"]
            self.result_dict.setdefault(monitor, {})
            self.result_dict[monitor].setdefault("hijacker", [])
            self.result_dict[monitor]["hijacker"] = list(self.col.aggregate(pipeline))

        for monitor, pairs in self.result_dict.items():
            self.monitor_list.append(monitor)
            self.victim_list.append(len(pairs["victim"]))
            self.hijacker_list.append(len(pairs["hijacker"]))