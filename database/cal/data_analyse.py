import pymongo
import sys 
from pprint import pprint

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


def get_datasets_infer(database_num_l):
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
                if len(item['as_path']) == 0:
                    continue

                dataset_raw[dataset_prefix[i]].setdefault(item['collector'], {}).update(
                    {(item['peer_asn'], item['peer_address']): len(item['as_path'])}
                )
        
        # 规整原始数据 - dataset_raw
        for collector in dataset_raw['victim'].keys():
            for pair in dataset_raw['victim'][collector].keys():
                dataset_raw['hijacker'].setdefault(collector, {}).setdefault(pair, float('inf'))
        for collector in dataset_raw['hijacker'].keys():
            for pair in dataset_raw['hijacker'][collector].keys():
                dataset_raw['victim'].setdefault(collector, {}).setdefault(pair, float('inf'))

        
        dataset_raw_l.append(dataset_raw)
    
    # dataset_raw = combine_several_neighbors(dataset_raw_l)
    # 处理多个dataset_raw 对应多个neighbor的情况
    dataset_mid_l = list()
    for dataset_raw in dataset_raw_l:
        for collector in dataset_raw['victim'].keys():
            # 计算差值集 - dataset_mid_l
            dataset_mid[collector] = {}
            for pair, val in dataset_raw['victim'][collector].items():
                dataset_mid[collector][pair] = val - dataset_raw['hijacker'][collector][pair]
        dataset_mid_l.append(dataset_mid)

    dataset_mid = combine_several_neighbors_mid(dataset_mid_l)

    # 计算最大值 - dataset_fin
    for collector in dataset_mid.keys():
        max_len = float('-inf')
        for val in dataset_mid[collector].values():
            if val > max_len:
                max_len = val
        dataset_fin[collector] = max_len

    return dataset_raw_l, dataset_mid_l, dataset_fin


def combine_several_neighbors_mid(dataset_mid_l):
    # 考虑如果有多个输入，合并中间体
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


def get_percent_infer(dataset_mid_l, hijacker_prepend_l, asn_only_mode=False, reverso_value=0.5, drop_inf=False, count_only=False, greater_than_zero_only=False):
    if type(dataset_mid_l) is not list:
        dataset_mid_l = [dataset_mid_l]

    if type(hijacker_prepend_l) is int:
        hijacker_prepend_l = [hijacker_prepend_l for _ in range(len(dataset_mid_l))]

    res = dict()
    collectors = set()

    for dataset_mid in dataset_mid_l:
        collectors |= set(dataset_mid.keys())

    for dataset_mid in dataset_mid_l:
        for collector in collectors:
            dataset_mid.setdefault(collector, {})

    # print(dataset_mid_l)

    count_dict = dict()
    dangerous_set_dict = dict()      

    for index in range(len(dataset_mid_l)):
        dataset_mid = dataset_mid_l[index]
        hijacker_prepend = hijacker_prepend_l[index]
        
        for monitor, value_pair_dict in dataset_mid.items():
            count_dict.setdefault(monitor, dict())
            dangerous_set_dict.setdefault(monitor, set())

            count_dict_temp = count_dict[monitor]
            dangerous_set = dangerous_set_dict[monitor]

            if asn_only_mode:
                temp_set = set()
                
            for value_pair, count in value_pair_dict.items():
                if drop_inf and count == float('inf'):
                    continue
                
                if asn_only_mode:
                    if value_pair[0] in temp_set:
                        continue
                    else:
                        temp_set.add(value_pair[0])

                reverso = 0
                if count > hijacker_prepend:
                    dangerous_set.add(value_pair[0])
                elif count == hijacker_prepend:
                    reverso = 1
                
                count_dict_temp[value_pair[0]] = count_dict_temp.get(value_pair[0], 0) + reverso_value ** reverso
            
            # if temp_sum > 0:
            #     if count_only:
            #         temp_sum = 1
            #     temp_percent = round(temp_dangerous / temp_sum, 3)
            
            # res.update({monitor: temp_percent})

    for monitor in count_dict.keys():
        dangerous_temp = 0
        sum_temp = 0
        percent_temp = 0
        for value_pair, count in count_dict[monitor].items():
            if value_pair in dangerous_set_dict[monitor]:
                dangerous_temp += count
        
        if count_only:
            sum_temp = 1
        else:
            sum_temp = sum(count_dict[monitor].values())

        if sum_temp > 0:
            percent_temp = round(dangerous_temp / sum_temp, 3)

        res.update({monitor: percent_temp})
        
    return {k: v for k, v in sorted(res.items(), key=lambda x: x[0]) if (v > 0 or not greater_than_zero_only)}


def get_percent_real(datapath, hijacker_prepend, intersect=True, remove_empty_monitors=True, count_only=False, greater_than_zero_only=False):
    datasets = jsonutils.parse_dataset_json(datapath)
    if intersect:
        jsonutils.intersect_peer_data(datasets)
    if remove_empty_monitors:
        jsonutils.remove_empty_monitors(datasets)
    
    dataset = datasets[hijacker_prepend-1]

    if count_only:
        count_counter = 0
    else:
        count_counter = 1
    
    res = {dataset.monitor_list[i]: round(dataset.hijacker_list[i] / ((dataset.victim_list[i] + dataset.hijacker_list[i]) ** count_counter), 3) \
        for i in range(len(dataset.monitor_list)) if dataset.victim_list[i] + dataset.hijacker_list[i] != 0}

    return {k: v for k, v in sorted(res.items(), key=lambda x: x[0]) if (v > 0 or not greater_than_zero_only)}

def rectification(dataset_per_infer, dataset_per_real, align_to_which=2):
    '''
    align_to_which:
        0: 对齐dataset_per_infer
        1: 对齐dataset_per_real
        else/default: 双补全
    '''
    align_list = list()
    if align_to_which == 0:
        align_list = dataset_per_infer.keys()
    elif align_to_which == 1:
        align_list = dataset_per_real.keys()
    else:
        align_list = list(set(dataset_per_infer.keys()) | set(dataset_per_real.keys()))

    res_infer = {align: dataset_per_infer.get(align, 0.0) for align in align_list}
    res_real = {align: dataset_per_real.get(align, 0.0) for align in align_list}

    return res_infer, res_real


def get_report(dataset_per_infer, dataset_per_real):
    rt_dataset_per_infer, rt_dataset_per_real = rectification(dataset_per_infer, dataset_per_real, align_to_which=2)

    monitors = rt_dataset_per_infer.keys()
    total_len = len(monitors)
    if total_len == 0:
        return None
    
    clean_dict = dict()

    fp_num = 0
    fp_dict = dict()
    fn_num = 0
    fn_dict = dict()
    
    diff_dict = dict()
    diff_per_dict = dict()

    for monitor in monitors:
        if rt_dataset_per_infer[monitor] == 0:
            fn_num += 1
            fn_dict.update(dict({monitor: round(rt_dataset_per_infer[monitor] - rt_dataset_per_real[monitor])}))
        elif rt_dataset_per_real[monitor] == 0:
            fp_num += 1
            fp_dict.update(dict({monitor: round(rt_dataset_per_infer[monitor] - rt_dataset_per_real[monitor], 3)}))
        else:
            diff_dict.update(dict({monitor: round(rt_dataset_per_infer[monitor] - rt_dataset_per_real[monitor], 3)}))
            diff_per_dict.update(dict({monitor: round((rt_dataset_per_infer[monitor] - rt_dataset_per_real[monitor]) / rt_dataset_per_real[monitor], 3)}))
        clean_dict.update({monitor: (rt_dataset_per_infer[monitor], rt_dataset_per_real[monitor])})
        

    fp_rate = round(fp_num / total_len, 3)
    fn_rate = round(fn_num / total_len, 3)


    return ((fp_rate, fn_rate), (fp_dict, fn_dict, diff_dict, diff_per_dict), clean_dict)



if __name__ == '__main__':
    
    hijacking_exp_num_l = [48]

    for hijacking_exp_num in hijacking_exp_num_l:
        print(f'\n!!!!!!!!!!!!!!!!!!!!!!{hijacking_exp_num}!!!!!!!!!!!!!!!!!!!!!!')
        base_exp_num = hijacking_exp_num + 1

        prepend_num_l = [i+1 for i in range(4)]
        _, dataset_mid, dataset_fin = get_datasets_infer(base_exp_num)
        print(dataset_fin)
        print(f"predict value: {max([x for x in dataset_fin.values() if x != float('inf')])}")

        for prepend_num in prepend_num_l:
            dataset_per_infer_asn = get_percent_infer(dataset_mid, prepend_num, reverso_value=1, asn_only_mode=True, greater_than_zero_only=False)
            dataset_per_infer_prefix = get_percent_infer(dataset_mid, prepend_num, reverso_value=1, asn_only_mode=False, greater_than_zero_only=False)
            dataset_per_real_asn = get_percent_real(f'../data/a_184_164_236_0=24-{hijacking_exp_num}.json', prepend_num, intersect=False, greater_than_zero_only=False)
            dataset_per_real_prefix = get_percent_real(f'../data/p_184_164_236_0=24-{hijacking_exp_num}.json', prepend_num, intersect=False, greater_than_zero_only=False)


            (fp_rate_asn, fn_rate_asn), (fp_dict_asn, fn_dict_asn, diff_dict_asn, diff_per_dict_asn), clean_dict_asn = get_report(dataset_per_infer_asn, dataset_per_real_asn)
            (fp_rate_prefix, fn_rate_prefix), (fp_dict_prefix, fn_dict_prefix, diff_dict_prefix, diff_per_dict_prefix), clean_dict_prefix = get_report(dataset_per_infer_prefix, dataset_per_real_prefix)

            print()
            print(f'=======Result of prepend {prepend_num}=======')
            print(f'fp_rate_asn: {fp_rate_asn}, fn_rate_asn: {fn_rate_asn}')
            print(f'fp_rate_prefix: {fp_rate_prefix}, fn_rate_prefix: {fn_rate_prefix}')
            print('-------clean_dict_asn-------')
            pprint(clean_dict_asn)
            print(f'-------diff_dict_asn-------')
            pprint(diff_dict_asn)
            print(f'average: {round(sum([abs(x) for x in diff_dict_asn.values()]) / len(diff_dict_asn.values()), 3)}')
            print(f'-------diff_per_dict_asn-------')
            pprint(diff_per_dict_asn)
            print(f'average: {round(sum([abs(x) for x in diff_per_dict_asn.values()]) / len(diff_per_dict_asn.values()), 3)}')

            print('-------clean_dict_prefix-------')
            pprint(clean_dict_prefix)
            break


    # hijacking_exp_num = 