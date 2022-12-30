from matplotlib import pyplot as plt
import pymongo
from datautils import DataManager, GenedDataSet
import json

import dataclasses
@dataclasses.dataclass
class GenedDataSet:
    as_path: list

    result_dict: dict

    monitor_list: list
    victim_list: list
    hijacker_list: list


def gen_datasets(cols: list, aspaths: list, vic_prepend: int = 0, asn_only=True):
    data_manager = DataManager(asn_only)

    datasets = list()
    for i in range(len(cols)):
        temp = data_manager.gen_dataset(aspaths[i], cols[i], vic_prepend)
        temp_new = GenedDataSet(temp.as_path, temp.result_dict, temp.monitor_list, temp.victim_list, temp.hijacker_list)
        datasets.append(temp_new)
    
    return datasets


class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)


def write_to_json(datasets: list, filename: str):
    with open(filename, "w") as outfile:
        json.dump(datasets, outfile, cls=JSONEncoder)


if __name__ == '__main__':
    pair_dict = {
        32: 4,
        34: 4,
        36: 4,
        38: 4,
        40: 4,
        42: 4,
        44: 4,
        46: 3,
        48: 3,
        50: 2,
        52: 2,
        54: 1,
        56: 1,
        58: 0,
        60: 0
    }

    # num = 40
    for num, prepend_times in pair_dict.items():
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
        mydb = myclient["updates"]
        cols = [
            mydb[f"184.164.236.0/24_1-{num}"],
            mydb[f"184.164.236.0/24_2-{num}"],
            mydb[f"184.164.236.0/24_3-{num}"],
            mydb[f"184.164.236.0/24_4-{num}"]
        ]
        aspaths = [[61575, 61576],
                    [61575, 61575, 61576],
                    [61575, 61575, 61575, 61576],
                    [61575, 61575, 61575, 61575, 61576]
                    ]
            
        datasets_asn = gen_datasets(cols, aspaths, prepend_times, True)
        datasets_pre = gen_datasets(cols, aspaths, prepend_times, False)

        file_name_asn = f"./data/a_184_164_236_0=24-{num}.json"
        file_name_pre = f"./data/p_184_164_236_0=24-{num}.json"

        print(file_name_asn)
        write_to_json(datasets_asn, file_name_asn)
        print(file_name_pre)
        write_to_json(datasets_pre, file_name_pre)