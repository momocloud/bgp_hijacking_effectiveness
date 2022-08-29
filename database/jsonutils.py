import json
from dataclasses import dataclass
from copy import deepcopy
from matplotlib import pyplot as plt

@dataclass
class GenedDataSet:
    as_path: list

    result_dict: dict

    monitor_list: list
    victim_list: list
    hijacker_list: list

    @classmethod
    def from_dict(cls, data: dict):
        return GenedDataSet(data['as_path'], data['result_dict'], data['monitor_list'], data['victim_list'], data['hijacker_list'])


def parse_dataset_json(file_path: str) -> list:
    datasets = list()
    with open(file_path, 'r') as f:
        dataset_dic_list = json.load(f)
        for data in dataset_dic_list:
            datasets.append(GenedDataSet.from_dict(data))
    return datasets


def remove_empty_monitors(datasets: list):
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

def plot_peers(datasets: list, fig_name: str):
    fig_num = len(datasets)
    fig, ax=plt.subplots(fig_num,1,figsize=(18,3.7*fig_num))
    bar_width = 0.4
    for i in range(fig_num):
        ax[i].set_title(f'Type {i+1}', fontsize=17, fontweight='bold')
        x_ticks = [monitor.replace('route-views', 'rv') for monitor in datasets[i].monitor_list]
        bar1 = ax[i].bar(x=x_ticks, height=datasets[i].victim_list, width=bar_width, color='b')
        bar2 = ax[i].bar(x=x_ticks, height=datasets[i].hijacker_list, width=bar_width,
                bottom=datasets[i].victim_list, color='r')

        ax[i].set_ylabel('collector peers', fontsize=20, fontweight='bold')
        ax[i].set_ylim(0, 60)
        yticks = [int(i) for i in ax[i].get_yticks()]
        ax[i].set_yticks(yticks)
        ax[i].set_yticklabels(yticks, fontsize=18, fontweight='bold')

        if i == fig_num-1:
            ax[i].set_xticks(x_ticks)
            ax[i].set_xticklabels(x_ticks, rotation=45, ha='right', fontsize=16, fontweight='bold')
        else:
            ax[i].set_xticks(['']*len(datasets[i].monitor_list))
        ax[i].legend((bar1, bar2), ('Victim: wisc01 (prepend 2) | Asn: 61576', 'Hijacker: grnet01 | Asn: 61575'), prop={'size': 14, 'weight': 'bold'})
    print(fig_name)
    plt.savefig(fig_name, format='pdf', bbox_inches='tight')
    plt.show()


def intersect_peer_data(datasets: list):
    peer_sets = list()
    for dataset in datasets:
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
    
    for num in pair_dict.keys():
        datasets = parse_dataset_json(f'./data/a_184_164_236_0=24-{num}.json')
        intersect_peer_data(datasets)
        empty_monitor_list = remove_empty_monitors(datasets)
        plot_peers(datasets, f'./figures/a_184_164_236_0=24-{num}.pdf')