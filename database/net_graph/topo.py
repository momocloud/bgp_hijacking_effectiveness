from matplotlib import pyplot as plt
import numpy as np
import matplotlib as mpl
import pymongo
from copy import deepcopy
import os
import json
from pyecharts.charts import Graph
from pyecharts import options as opts
from pyecharts.options import LineStyleOpts
from math import log2


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


def build_up_edges(as_path: list, remove_prepend: bool, victim_as=61576, hijacker_as=61575) -> list:
    victim_as = str(victim_as)
    hijacker_as = str(hijacker_as)
    index = 0
    while index < len(as_path)-1:
        if as_path[index] == hijacker_as and as_path[index+1] == victim_as:
            as_path[index+1] = f'{as_path[index+1]}_fake'
            break
        index += 1


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

    
    as_path_back = as_path.copy()
    as_path_back.append(as_path_back.pop(0))
    returned_list = list(zip(as_path, as_path_back))
    returned_list.pop()

    return returned_list


def plot_topo(data_source: str, vic_pipeline, hij_pipelines, cols_or_jsonaddrs, exp_num: int, remove_prepend: bool = True, output_root: str='./topo_plot/', unit_nums: list=None):
    assert data_source in ['db', 'json']
    if data_source == 'db':
        get_aspath = get_aspaths_from_db
    else:
        get_aspath = get_aspaths_from_json

    if unit_nums is None:
        unit_nums = [i+1 for i in range(4)]

    hij_line_style = LineStyleOpts(color="red", curve=0.1, opacity=0.5)
    vic_line_style = LineStyleOpts(color="blue", curve=0.1, opacity=0.5)
    both_line_style = LineStyleOpts(color="green", curve=0.1, opacity=0.5)

    graphs = []
    for _ in range(len(unit_nums)):
        graphs.append(Graph(init_opts=opts.InitOpts(width="2000px", height="1500px")))

    for index in range(len(graphs)):
        graph = graphs[index]
        vic_edges = []
        hij_edges = []

        for as_path in get_aspath(vic_pipeline, cols_or_jsonaddrs[index]):
            vic_edges.extend(build_up_edges(as_path, remove_prepend))
        for as_path in get_aspath(hij_pipelines[index], cols_or_jsonaddrs[index]):
            hij_edges.extend(build_up_edges(as_path, remove_prepend))

        nodes_dict = dict()
        for vic_edge in vic_edges:
            if nodes_dict.setdefault(vic_edge[0], {"value": 0, "cat": 0})["cat"] == 1:
                nodes_dict[vic_edge[0]]["cat"] = 2
            nodes_dict[vic_edge[0]]["value"] += 1
            if nodes_dict.setdefault(vic_edge[1], {"value": 0, "cat": 0})["cat"] == 1:
                nodes_dict[vic_edge[1]]["cat"] = 2
            nodes_dict[vic_edge[1]]["value"] += 1

        for hij_edge in hij_edges:
            if nodes_dict.setdefault(hij_edge[0], {"value": 0, "cat": 1})["cat"] == 0:
                nodes_dict[hij_edge[0]]["cat"] = 2
            nodes_dict[hij_edge[0]]["value"] += 1
            if nodes_dict.setdefault(hij_edge[1], {"value": 0, "cat": 1})["cat"] == 0:
                nodes_dict[hij_edge[1]]["cat"] = 2
            nodes_dict[hij_edge[1]]["value"] += 1

        nodes = list()
        # {"name": as, "value": times, "category"}
        # cat: {0: vic, 1: hij, 2: both}
        for node, node_val in nodes_dict.items():
            node_attr = {
                "name": node,
                "value": node_val["value"],
                "category": node_val["cat"],
                "symbolSize": 5.5*log2(node_val["value"])+3,
                "itemStyle": { "normal":{
                    "color": {
                        0: "blue",
                        1: "red",
                        2: "green"
                    }[node_val["cat"]]
                }}
            }
            nodes.append(node_attr)

        links = []
        for vic_edge in vic_edges:
            if vic_edge not in hij_edges:
                links.append({
                    "source": vic_edge[0],
                    "target": vic_edge[1],
                    "lineStyle": vic_line_style
                })
            else:
                links.append({
                    "source": vic_edge[0],
                    "target": vic_edge[1],
                    "lineStyle": both_line_style
                })
        for hij_edge in hij_edges:
            if hij_edge not in vic_edges:
                links.append({
                    "source": hij_edge[0],
                    "target": hij_edge[1],
                    "lineStyle": hij_line_style
                })
            else:
                links.append({
                    "source": hij_edge[0],
                    "target": hij_edge[1],
                    "lineStyle": both_line_style
                })

        categories = [
            {"name": "Victim", 
                "itemStyle": { "normal": {
                            "color": 'blue'
                        }}}, 
            {"name": "Hijacker",
                        "itemStyle": { "normal": {
                            "color": 'red'
                        }}}, 
            {"name": "Both", 
                        "itemStyle": { "normal": {
                            "color": 'green'
                        }}}]

        _ = (
            graph
                .add(
                    "",
                    nodes=nodes,
                    links=links,
                    categories=categories,
                    is_draggable=True,
                    is_roam=True,
                    repulsion=4000,
                    edge_symbol=['circle', 'arrow'],
                    layout="force",
                    edge_symbol_size=4,
                    # gravity=0.75
            ).render(os.path.join(output_root, f"graph_vic_hij{exp_num}-{unit_nums[index]}.html"))
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

        # plot_topo('db', vic_pipeline, hij_pipelines, cols, exp_num)
        plot_topo('json', vic_pipeline, hij_pipelines, jsonaddrs, exp_nums[i], remove_prepend=True)

    jsonaddrs = jsonaddr_init(24, unit_nums=[4])
    path_matched = path_matched_init(prepend_time=0, unit_nums=[4])
    vic_pipeline, hij_pipelines = pipe_init(path_matched)
    plot_topo('json', vic_pipeline, hij_pipelines, jsonaddrs, 24, remove_prepend=True, unit_nums=[4])
