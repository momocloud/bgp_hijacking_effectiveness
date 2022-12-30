from matplotlib import pyplot as plt
import numpy as np
import matplotlib as mpl
import pymongo
from copy import deepcopy
import os
import json
from pyecharts import options as opts
from pyecharts.charts import Tree
from pprint import pprint


class TreeNode:
    def __init__(self, name: str, item_style: dict=None, line_style: dict=None, label: dict=None, children: list=None):
        self.name = name
        if children is None:
            self.children = list()
        self.itemStyle = item_style
        self.lineStyle = line_style
        self.label = label
        
    def __repr__(self):
        return f'name: {self.name} | itemStyle: {self.itemStyle} | lineStyle: {self.lineStyle} | label: {self.label} | len(children): {len(self.children)}'


def database_init(exp_num: int, database_addr: str='mongodb://localhost:27017/', unit_nums: list=None):
    client = pymongo.MongoClient(database_addr)
    db = client["updates"]
    if unit_nums is None:
        unit_nums = [i+1 for i in range(4)]
    cols = [
        db[f"184.164.236.0/24_{i}-{exp_num}"] for i in unit_nums
    ]
    return cols


def jsonaddr_init(exp_num: int, jsonpath_root: str='./rawdata_json/', unit_nums: list=None):
    if unit_nums is None:
        unit_nums = [i+1 for i in range(4)]
    jsonaddrs = [
        os.path.join(jsonpath_root, f'184.164.236.0_24_{i}-{exp_num}.json') for i in unit_nums
    ]
    return jsonaddrs


def path_matched_init(prepend_time=0, victim_as=61576, hijacker_as=61575, unit_nums: list=None):
    victim_as = str(victim_as)
    hijacker_as = str(hijacker_as)
    if unit_nums is None:
        unit_nums = [i+1 for i in range(4)]
    path_matched = [[victim_as] * (prepend_time+1)]
    path_matched += [
        [hijacker_as] * i +[victim_as] for i in unit_nums
    ]
    return path_matched


def pipe_init(path_matched: list, pipeaddr: str='./pipe_bias.json'):
    with open(pipeaddr, 'r') as f:
        pipe_bias = json.load(f)
    
    pipelines = []
    for aspath in path_matched:
        pipe = deepcopy(pipe_bias)
        pipe[1]["$match"]["$expr"]["$eq"][1] += [str(aselem) for aselem in aspath]
        pipe[1]["$match"]["$expr"]["$eq"][0]["$slice"][1] -= len(aspath)
        pipelines.append(pipe)
    vic_pipeline = pipelines.pop(0)
    hij_pipelines = pipelines

    return vic_pipeline, hij_pipelines


def get_aspaths_from_db(pipeline: list, col: pymongo.collection.Collection) -> list:
    cursor = col.aggregate(pipeline)
    aspaths = list()
    for doc in cursor:
        aspaths.append(doc['_id'])
    aspaths.sort()
    return aspaths


def get_aspaths_from_json(pipeline: list, jsonaddr: str) -> list:
    path_matched = pipeline[1]['$match']['$expr']['$eq'][1]
    len_matched = len(path_matched)

    with open(jsonaddr, 'r') as f:
        jsondata = json.load(f)
    
    aspaths = list()
    for item in jsondata:
        each_aspath = item['as_path']
        latest = item['latest']

        if latest and each_aspath[-len_matched:] == path_matched:
            aspaths.append(each_aspath)
    aspaths = list(set([str(i) for i in aspaths]))
    import ast
    aspaths = [ast.literal_eval(i) for i in aspaths]
    aspaths.sort()

    return aspaths


def build_up_tree_edges(as_path: list, remove_prepend: bool, victim_as=61576, hijacker_as=61575) -> list:
    if remove_prepend:
        index = 0
        while True:
            if index < len(as_path)-1:
                if as_path[index] == as_path[index+1]:
                    as_path.pop(index)
                else:
                    index += 1
            else: 
                break
    else:
        index = 0
        marked_as = ''
        marked_num = 1
        while index < len(as_path):
            if as_path[index] == marked_as:
                as_path[index] = f'{as_path[index]}_{marked_num}'
                marked_num += 1
            else:
                marked_as = as_path[index]
                marked_num = 1
            index += 1

    as_path.reverse()

    return as_path


def plot_tree(data_source: str, vic_pipeline, hij_pipelines, cols_or_jsonaddrs, exp_num: int, remove_prepend: bool = True, output_root: str='./tree_plot/', unit_nums: list=None, layout='orthogonal', orient='LR'):
    vic_as = hij_pipelines[0][1]['$match']['$expr']['$eq'][1][-1]

    assert data_source in ['db', 'json']
    if data_source == 'db':
        get_aspath = get_aspaths_from_db
    else:
        get_aspath = get_aspaths_from_json

    if unit_nums is None:
        unit_nums = [i+1 for i in range(4)]

    vic_item_style = vic_label = {'color': 'blue'}
    hij_item_style =  hij_label = {'color': 'red'}
    vic_line_style = {'color': '#acaffd'}
    hij_line_style = {'color': '#ffb9b5'}
    vic_item_style.update({'borderColor': 'blue'})
    hij_item_style.update({'borderColor': 'red'})

    trees = []
    for _ in range(len(unit_nums)):
        trees.append(Tree(init_opts=opts.InitOpts(width="4000px", height="3000px")))

    for index in range(len(trees)):
        tree = trees[index]
        vic_edges = list()
        hij_edges = list()

        for as_path in get_aspath(vic_pipeline, cols_or_jsonaddrs[index]):
            vic_edges.append(build_up_tree_edges(as_path, remove_prepend))
        for as_path in get_aspath(hij_pipelines[index], cols_or_jsonaddrs[index]):
            hij_edges.append(build_up_tree_edges(as_path, remove_prepend))

        vic_node_dict = dict()
        hij_node_dict = dict()

        for vic_edge in vic_edges:
            if len(vic_edge) < 2:
                continue
            
            root_str = vic_edge[0]
            node_pointer, dict_pointer = vic_node_dict.setdefault(root_str, (TreeNode(name=root_str, item_style=vic_item_style, label=vic_label), dict()))

            for i in range(1, len(vic_edge)):
                if vic_edge[i] not in dict_pointer.keys():
                    new_node = TreeNode(name=vic_edge[i], item_style=vic_item_style, line_style=vic_line_style, label=vic_label)
                    node_pointer.children.append(new_node)
                    node_pointer, dict_pointer = dict_pointer.setdefault(vic_edge[i], (new_node, dict()))
                else:
                    node_pointer, dict_pointer = dict_pointer.get(vic_edge[i])

        for hij_edge in hij_edges:
            if len(hij_edge) < 2:
                continue
            
            root_str = hij_edge[0]
            node_pointer, dict_pointer = hij_node_dict.setdefault(root_str, (TreeNode(name=root_str, item_style=hij_item_style, label=hij_label), dict()))

            for i in range(1, len(hij_edge)):
                if hij_edge[i] not in dict_pointer.keys():
                    new_node = TreeNode(name=hij_edge[i], item_style=hij_item_style, line_style=hij_line_style, label=hij_label)
                    node_pointer.children.append(new_node)
                    node_pointer, dict_pointer = dict_pointer.setdefault(hij_edge[i], (new_node, dict()))
                else:
                    node_pointer, dict_pointer = dict_pointer.get(hij_edge[i])


        try:
            data_root = vic_node_dict[vic_as][0]
            try:
                data_root.children.extend(hij_node_dict[vic_as][0].children)
            except:
                print('WARN: No hijacker tree!')
        except:
            print('WARN: No victim tree!')
            try:
                data_root = hij_node_dict[vic_as][0]
                data_root.label = vic_label
            except:
                print('WARN: No hijacker tree!')
        datastr = json.dumps(data_root, default=lambda o: o.__dict__)
        data = [json.loads(datastr)]

        _ = (
            tree
                .add("", data=data, symbol="emptyCircle", 
                    label_opts=opts.LabelOpts(color='white'), initial_tree_depth=-1, layout=layout, orient=orient, is_roam=True)
                .render(os.path.join(output_root, f"tree_vic_hij{exp_num}-{unit_nums[index]}.html"))
        )



if __name__ == "__main__":
    exp_nums = [32, 34, 36, 38, 40, 42, 44, 46, 48, 52, 56, 60]
    prepend_times = [4, 4, 4, 4, 4, 4, 4, 3, 3, 2, 1, 0]
    assert len(exp_nums) == len(prepend_times)
    
    for i in range(len(exp_nums)):

        # cols = database_init(exp_num)
        jsonaddrs = jsonaddr_init(exp_nums[i])

        path_matched = path_matched_init(prepend_time=prepend_times[i])
        vic_pipeline, hij_pipelines = pipe_init(path_matched)

        # plot_tree('db', vic_pipeline, hij_pipelines, cols, exp_num)
        '''
        layout: 'orthogonal', 'radial'
        orient (valid while orthogonal):  'LR' , 'RL', 'TB', 'BT'
        '''
        plot_tree('json', vic_pipeline, hij_pipelines, jsonaddrs, exp_nums[i], remove_prepend=True, layout='orthogonal', orient='TB')

    jsonaddrs = jsonaddr_init(24, unit_nums=[4])
    path_matched = path_matched_init(prepend_time=0, unit_nums=[4])
    vic_pipeline, hij_pipelines = pipe_init(path_matched)
    plot_tree('json', vic_pipeline, hij_pipelines, jsonaddrs, 24, remove_prepend=True, layout='orthogonal', orient='TB', unit_nums=[4])