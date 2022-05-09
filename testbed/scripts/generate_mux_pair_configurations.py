import argparse
from itertools import combinations
import os
import utils
import random

PEERING_PREFIX = "184.164.236.0/24"
VICTIM = 61574 
HIJACKER = 61575
DIR_TYPE = "pair"
MUX_PATH = "./meta_configs/valid_muxes.json"
ASN_PATH = "./meta_configs/valid_asns.json"
PREFIX_PATH = "./meta_configs/valid_prefixes.json"

parser = argparse.ArgumentParser(description="produce all pairwise experiment configurations")
parser.add_argument('-o', '--output_root_dir', dest='out_dir', type=str,
                    help='the root of output directory', default="./exp_confs")
parser.add_argument('-t', '--type', dest='exp_type', choices=['A', 'W', 'B'],
                    help='type of experiment', required=True)
parser.add_argument('-n', '--type_num', dest='type_num', type=int,
                    help='the number of hijacking type, default is 1', default=1)
parser.add_argument('-j', '--hijacker_asn', dest='hijacker_asn', type=int,
                    help='the ASN of hijacker, default is 61575', default=HIJACKER)
parser.add_argument('-v', '--victim_asn', dest='victim_asn', type=int,
                    help='the ASN of victim, default is 61574', default=VICTIM)
parser.add_argument('-p', '--peering_prefix', dest='peering_prefix', type=str,
                    help='the prefix of peering, default is 184.164.236.0/24', default=PEERING_PREFIX)
args = parser.parse_args()

assert os.path.isfile(MUX_PATH)
assert os.path.isfile(ASN_PATH)
assert os.path.isfile(PREFIX_PATH)

muxes = utils.load_json(MUX_PATH).get("up", [])

HIJACKER = args.hijacker_asn
assert HIJACKER in utils.load_json(ASN_PATH).get("up", [])
VICTIM = args.victim_asn
assert VICTIM in utils.load_json(ASN_PATH).get("up", [])
PEERING_PREFIX = args.peering_prefix
assert PEERING_PREFIX in utils.load_json(PREFIX_PATH).get("up", [])

asn_left = list(set(utils.load_json(ASN_PATH).get("up", [])) - {HIJACKER, VICTIM})

if args.exp_type in 'AB':
    if args.type_num <= 0:
        as_path = [HIJACKER]
    else:
        as_path = [HIJACKER]*args.type_num + [VICTIM]

out_dir = os.path.join(args.out_dir, DIR_TYPE)


for mux_pair in combinations(muxes, 2):
    out_dir = os.path.join(out_dir, f'h_{mux_pair[1]}-v_{mux_pair[0]}', f'h_{HIJACKER}-v_{VICTIM}', f'type{args.type_num}')
    announce_out_dir = os.path.join(out_dir, 'announcement')
    withdrawal_out_dir = os.path.join(out_dir, 'withdrawal')
    utils.create_dir(announce_out_dir)
    utils.create_dir(withdrawal_out_dir)

    # ANNOUNCEMENT
    if args.exp_type in 'AB':
        # VICTIM
        exp_conf = {
            PEERING_PREFIX: {
                "announce": [
                    {
                        "muxes": [
                            mux_pair[0]
                        ],
                        "origin": VICTIM
                    }
                ]
            }
        }
        utils.dump_json(f"{announce_out_dir}/announce_victim_{mux_pair[0]}.json", exp_conf, indent=2)

        #HIJACKER
        exp_conf = {
            PEERING_PREFIX: {
                "announce": [
                    {
                        "muxes": [
                            mux_pair[1]
                        ],
                        "origin": as_path[-1],
                        "prepend": as_path[:-1]
                    }
                ]
            }
        }
        utils.dump_json(f"{announce_out_dir}/announce_hijacker_{mux_pair[1]}.json", exp_conf, indent=2)

    #WITHDRAW
    if args.exp_type in 'WB':
        exp_conf = {
            PEERING_PREFIX: {
                "withdraw": [
                    mux_pair[0],
                    mux_pair[1]
                ]
            }
        }
        utils.dump_json(f"{withdrawal_out_dir}/withdraw_{mux_pair[0]}_{mux_pair[1]}.json", exp_conf, indent=2)