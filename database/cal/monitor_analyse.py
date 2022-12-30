from dataclasses import dataclass, field
import pymongo
import sys 
from pprint import pprint
import re

sys.path.append("..") 
import jsonutils

def get_cols(num):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["updates"]
    cols = [
        mydb[f"184.164.236.0/24_b-{num}"],
        mydb[f"184.164.237.0/24_b-{num}"],
    ]

    return cols


def is_ipv4(zmx):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(zmx):
        return True
    else:
        return False


@dataclass
class MonitorData:
    neighbor_num: int
    neighbor_prepend: int

    collector: str
    peer_address: str
    distance: int

    all_dangerous_set: set = field(repr=False)
    all_monitor_set: set = field(repr=False)

    @property
    def is_dangerous(self):
        return self.distance >= self.neighbor_prepend or self.origin_info in self.all_dangerous_set

    @property
    def is_dangerous_pure(self):
        return self.distance > self.neighbor_prepend or self.origin_info in self.all_dangerous_set

    @property
    def origin_info(self):
        return (self.collector, self.peer_address)


def get_datasets_infer_monitor(database_num_l, remove_positive_inf=False):
    if type(database_num_l) is int:
        database_num_l = [database_num_l]

    dataset_raw_l = list()
    for database_num in database_num_l:
        cols = get_cols(database_num)
        
        dataset_prefix = ["victim", "hijacker"]
        dataset_raw = {}
        dataset_mid = {}
        dataset_fin = {}

        query_dict = {'latest': True}
        show_dict = {'_id': 0, 'router': 0, 'time': 0}

        for i, col in enumerate(cols):
            dataset_raw[dataset_prefix[i]] = {}
            for item in col.find(query_dict, show_dict):
                if len(item['as_path']) == 0 or not is_ipv4(item['peer_address']):
                    continue

                dataset_raw[dataset_prefix[i]].setdefault(item['collector'], {}).update(
                    {(item['peer_asn'], item['peer_address']): len(item['as_path'])}
                )
        
        # 规整原始数据 - dataset_raw
        # aligning raw data - dataset_raw
        for collector in dataset_raw['victim'].keys():
            for pair in dataset_raw['victim'][collector].keys():
                dataset_raw['hijacker'].setdefault(collector, {}).setdefault(pair, float('inf'))
        for collector in dataset_raw['hijacker'].keys():
            for pair in dataset_raw['hijacker'][collector].keys():
                dataset_raw['victim'].setdefault(collector, {}).setdefault(pair, float('inf'))

        
        dataset_raw_l.append(dataset_raw)
    
    # 处理多个dataset_raw 对应多个neighbor的情况，以获得准确的dataset_fin
    # handle multiple dataset_raw against multiple neighbours to get the exact dataset_fin
    dataset_mid_l = list()
    for dataset_raw in dataset_raw_l:
        for collector in dataset_raw['victim'].keys():
            # 计算差值集 - dataset_mid_l
            # calculating difference sets - dataset_mid_l
            dataset_mid[collector] = {}
            for pair, val in dataset_raw['victim'][collector].items():
                dataset_mid[collector][pair] = val - dataset_raw['hijacker'][collector][pair]
        dataset_mid_l.append(dataset_mid)

    dataset_mid = combine_several_neighbors_mid(dataset_mid_l)

    # 计算最大值 - dataset_fin
    # calculate the maximum value needed to be invisiable completely - dataset_fin
    for collector in dataset_mid.keys():
        max_len = float('-inf')
        for val in dataset_mid[collector].values():
            if val > max_len:
                if remove_positive_inf and val > 1000000:
                    continue
                max_len = val
        dataset_fin[collector] = max_len

    return dataset_raw_l, dataset_mid_l, dataset_fin
    

def combine_several_neighbors_mid(dataset_mid_l):
    # 考虑如果有多个输入，合并中间体
    # consider merging intermediates if there are multiple inputs
    if len(dataset_mid_l) == 1:
        dataset_mid = dataset_mid_l[0]
    else:
        dataset_mid = dict()
        collector_set = set()
        for temp in dataset_mid_l:
            collector_set |= set(temp.keys())

        for collector in collector_set:
            dataset_mid.update({collector: {}})
            for temp in dataset_mid_l:
                data_pair = temp.get(collector, {})

                for key, value in data_pair.items():
                    if value < dataset_mid[collector].get(key, float('inf')):
                        dataset_mid[collector][key] = value
    
    return dataset_mid


def get_state_infer(dataset_mid_l, hijacker_prepend_l):
    if type(dataset_mid_l) is not list:
        dataset_mid_l = [dataset_mid_l]

    if type(hijacker_prepend_l) is int:
        hijacker_prepend_l = [hijacker_prepend_l for _ in range(len(dataset_mid_l))]

    collectors = set()

    for dataset_mid in dataset_mid_l:
        collectors |= set(dataset_mid.keys())

    for dataset_mid in dataset_mid_l:
        for collector in collectors:
            dataset_mid.setdefault(collector, {})

    monitors = list()
    all_dangerous_set = set()
    all_monitor_set = set()
    
    for index in range(len(dataset_mid_l)):
        dataset_mid = dataset_mid_l[index]
        hijacker_prepend = hijacker_prepend_l[index]

        for collector, value_pair_dict in dataset_mid.items():
            # print(dataset_mid)
            for (_, peer_address), distance in value_pair_dict.items():
                monitor = MonitorData(neighbor_num=index, neighbor_prepend=hijacker_prepend,
                    collector=collector, peer_address=peer_address, distance=distance, all_dangerous_set=all_dangerous_set, all_monitor_set=all_monitor_set)
                monitors.append(monitor)
                if monitor.is_dangerous:
                    all_dangerous_set.add(monitor.origin_info)
                all_monitor_set.add(monitor.origin_info)
    
    return monitors


def get_state_real(datapath, hijacker_prepend, intersect=False, remove_empty_monitors=True):
    datasets = jsonutils.parse_dataset_json(datapath)
    if intersect:
        jsonutils.intersect_peer_data(datasets)
    if remove_empty_monitors:
        jsonutils.remove_empty_monitors(datasets)
    
    dataset = datasets[hijacker_prepend-1].result_dict
    monitors = list()
    all_dangerous_set = set()
    all_monitor_set = set()

    for collector, hv_pair in dataset.items():
        h_part = hv_pair['hijacker']
        v_part = hv_pair['victim']

        for data_item in h_part:
            peer_address = data_item['_id']
            if not is_ipv4(peer_address):
                continue
            monitor = MonitorData(neighbor_num=-1, neighbor_prepend=hijacker_prepend, collector=collector,
                peer_address=peer_address, distance=-1, all_dangerous_set=all_dangerous_set, all_monitor_set=all_monitor_set)
            monitors.append(monitor)
            all_dangerous_set.add(monitor.origin_info)
            all_monitor_set.add(monitor.origin_info)
        
        for data_item in v_part:
            peer_address = data_item['_id']
            if not is_ipv4(peer_address):
                continue
            monitor = MonitorData(neighbor_num=-1, neighbor_prepend=hijacker_prepend, collector=collector,
                peer_address=peer_address, distance=-1, all_dangerous_set=all_dangerous_set, all_monitor_set=all_monitor_set)
            monitors.append(monitor)
            all_monitor_set.add(monitor.origin_info)

    return monitors
    

def get_roc(real_num, infer_num_l):
    if type(infer_num_l) is int:
        infer_num_l = [infer_num_l]
    
    fpr_l = list()
    tpr_l = list()

    for prepend_num in range(4):
        dataset_real = get_state_real(f'../data/p_184_164_236_0=24-{real_num}.json', prepend_num)
        dataset_infer = get_state_infer(get_datasets_infer_monitor(infer_num_l)[1], prepend_num)

        dataset_real_total_set = dataset_real[0].all_monitor_set
        dataset_real_dangerous_set = dataset_real[0].all_dangerous_set
        # dataset_real_dangerous_rate = round(len(dataset_real_dangerous_set) / len(dataset_real_total_set), 3)

        dataset_infer_total_set = dataset_infer[0].all_monitor_set
        dataset_infer_dangerous_set = dataset_infer[0].all_dangerous_set
        # dataset_infer_dangerous_rate = round(len(dataset_infer_dangerous_set) / len(dataset_infer_total_set), 3)

        # dataset_total_set = dataset_real_total_set | dataset_infer_total_set

        fp = len(dataset_infer_dangerous_set - dataset_real_dangerous_set)
        fn = len((dataset_infer_total_set - dataset_infer_dangerous_set) - (dataset_real_total_set - dataset_real_dangerous_set))

        tp = len(dataset_infer_dangerous_set & dataset_real_dangerous_set)
        tn = len((dataset_infer_total_set - dataset_infer_dangerous_set) & (dataset_real_total_set - dataset_real_dangerous_set))

        tpr = round(tp / (tp + fn), 3)
        fpr = round(fp / (fp + tn), 3)

        # recall = tpr
        # precision = round(tp / (tp + fp), 3)

        fpr_l.append(fpr)
        tpr_l.append(tpr)


    return (real_num, (fpr_l, tpr_l))
        


# if __name__ == '__main__':

#     real_num = 60
#     infer_num_l = [61]
#     for prepend_num in range(4):
#         dataset_real = get_state_real(f'../data/p_184_164_236_0=24-{real_num}.json', prepend_num)
#         dataset_infer = get_state_infer(get_datasets_infer_monitor(infer_num_l)[1], prepend_num)

#         dataset_real_total_set = dataset_real[0].all_monitor_set
#         dataset_real_dangerous_set = dataset_real[0].all_dangerous_set
#         dataset_real_dangerous_rate = round(len(dataset_real_dangerous_set) / len(dataset_real_total_set), 3)

#         dataset_infer_total_set = dataset_infer[0].all_monitor_set
#         dataset_infer_dangerous_set = dataset_infer[0].all_dangerous_set
#         dataset_infer_dangerous_rate = round(len(dataset_infer_dangerous_set) / len(dataset_infer_total_set), 3)

#         dataset_total_set = dataset_real_total_set | dataset_infer_total_set

#         fp = len(dataset_infer_dangerous_set - dataset_real_dangerous_set)
#         fn = len((dataset_infer_total_set - dataset_infer_dangerous_set) - (dataset_real_total_set - dataset_real_dangerous_set))

#         tp = len(dataset_infer_dangerous_set & dataset_real_dangerous_set)
#         tn = len((dataset_infer_total_set - dataset_infer_dangerous_set) & (dataset_real_total_set - dataset_real_dangerous_set))

#         tpr = round(tp / (tp + fn), 3)
#         fpr = round(fp / (fp + tn), 3)

#         recall = tpr
#         precision = round(tp / (tp + fp), 3)


#         # fp_rate = round(len(dataset_infer_dangerous_set - dataset_real_dangerous_set) / len(dataset_total_set), 3)
#         # fn_rate = round(len(dataset_real_dangerous_set - dataset_infer_dangerous_set) / len(dataset_total_set), 3)

#         # tp_rate = round(len(dataset_infer_dangerous_set & dataset_real_dangerous_set) / len(dataset_total_set), 3)
#         # tn_rate = round(len((dataset_infer_total_set - dataset_infer_dangerous_set) & (dataset_real_total_set - dataset_real_dangerous_set)) / len(dataset_total_set), 3)

#         misalarm_count = 0
#         miscarriage_count = 0
#         for monitor_real in dataset_real_total_set:
#             if monitor_real in dataset_real_dangerous_set and not monitor_real in dataset_infer_dangerous_set:
#                 misalarm_count += 1
#                 miscarriage_count += 1
#             if monitor_real in dataset_real_dangerous_set and not monitor_real in dataset_infer_total_set:
#                 miscarriage_count += 1

#         misjustice_count = 0
#         temp_real_dangerous_set = dataset_real_dangerous_set.copy()
#         temp_infer_dangerous_set = dataset_infer_dangerous_set.copy()
#         for monitor in temp_real_dangerous_set:
#             if monitor in temp_infer_dangerous_set:
#                 temp_infer_dangerous_set.remove(monitor)
#             else:
#                 misjustice_count += 1
#         misjustice_count += len(temp_infer_dangerous_set)

            
#         alarm_accuracy = round((len(dataset_real_total_set) - misalarm_count) / len(dataset_real_total_set), 3)
#         miscarriage_accuracy = round((len(dataset_real_total_set) - miscarriage_count) / len(dataset_real_total_set), 3)
#         misjustice_accuracy = round((len(dataset_total_set) - misjustice_count) / len(dataset_total_set), 3)

#         print(f'''
# =============Real: {real_num} | Infer: {infer_num_l}=============
#             alarm accuracy rate (monitor in Real-dangerous but not in Infer-dangerous / total in Real): {alarm_accuracy}
#             miscarriage accuracy rate (monitor in Real-dangerous but not in Infer-dangerous or Infer-total / total in Real): {miscarriage_accuracy}
#             misjustice accuracy rate (monitor in Real-dangerous but not in Infer-dangerous or vice versa): {misjustice_accuracy}

#             dangerous rate in Infer dataset: {dataset_infer_dangerous_rate}
#             dangerous rate in Real dataset: {dataset_real_dangerous_rate}
            
#             True Positive rate: {tpr}
#             False Positive rate (in Infer but not in Real): {fpr}
#             precision rate: {precision}
#             True Nagitave rate: 
#             False Nagitave rate (not in Infer but in Real): 
# '''
#         )

if __name__ == '__main__':
    real_num_l = [32, 34, 36, 38, 40, 42, 44, 46, 48, 52, 56, 60]
    infer_num_l_l = [33, 35, 37, 39, 41, 43, 45, 47, 49, 53, 57, 61]
    assert len(real_num_l) == len(infer_num_l_l)
    res_l = list()
    import pandas as pd
    from collections import OrderedDict

    for i in range(len(real_num_l)):
        real_num = real_num_l[i]
        infer_num_l = infer_num_l_l[i]
        data = get_datasets_infer_monitor(infer_num_l)[2]
        data = {k:v for k, v in sorted(data.items())}

        k_list = [k.replace('route-views', 'rv') for k in data.keys()]
        v_list = [v for v in data.values()]

        data_tmp = OrderedDict()
        for k, v in data.items():
            if v > 10000:
                v = 13.5
            elif v < -10000:
                v = -5.5
            data_tmp[k.replace('route-views', 'rv')] = v
        data = data_tmp
        del data_tmp

        data_df = pd.DataFrame({'monitor_list': data.keys(), 'fin_list': data.values()})
        data_df.to_csv(f'../origin_data_fin/fin_184_164_236_0=24-{infer_num_l}.csv',index=False, sep=',')
        # res_l.append(get_roc(real_num, infer_num_l))


    # pprint(res_l)
