import argparse
import os
import utils
import random

PEERING_PREFIX = "184.164.236.0/24"
VICTIM = 61574 
HIJACKER = 61575
DIR_TYPE = "single"
MUX_PATH = "./meta_configs/valid_muxes.json"
ASN_PATH = "./meta_configs/valid_asns.json"
PREFIX_PATH = "./meta_configs/valid_prefixes.json"

parser = argparse.ArgumentParser(description="produce all pairwise experiment configurations")
parser.add_argument('-o', '--output_root_dir', dest='out_dir', type=str,
                    help='the root of output directory', default="./exp_confs")
parser.add_argument('-t', '--type', dest='exp_type', choices=['A', 'W'],
                    help='type of experiment', required=True)
parser.add_argument('-n', '--type_num', dest='type_num', type=int,
                    help='the number of hijacking type, default is 1', default=1)
parser.add_argument('-j', '--hijacker_asn', dest='hijacker_asn', type=int,
                    help='the ASN of hijacker, default is 61575', default=HIJACKER)
parser.add_argument('-v', '--victim_asn', dest='victim_asn', type=int,
                    help='the ASN of victim, default is 61574', default=VICTIM)
parser.add_argument('-p', '--peering_prefix', dest='peering_prefix', type=str,
                    help='the prefix of peering, default is 184.164.236.0/24', default=PEERING_PREFIX)
parser.add_argument('-m', '--peering_mux', dest='peering_mux', type=str,
                    help='the mux of peering, default is "amsterdam01"', default="amsterdam01")
parser.add_argument('-d', '--peers_id', dest='peers_id', type=str, nargs='+',
                    help='the id of peers, default is None', default=None)
args = parser.parse_args()

assert os.path.isfile(MUX_PATH)
assert os.path.isfile(ASN_PATH)
assert os.path.isfile(PREFIX_PATH)

muxes_on = utils.load_json(MUX_PATH).get("up", []) + utils.load_json(MUX_PATH).get("down", [])
mux = args.peering_mux
assert mux in muxes_on

HIJACKER = args.hijacker_asn
assert HIJACKER in utils.load_json(ASN_PATH).get("up", [])
VICTIM = args.victim_asn
assert VICTIM in utils.load_json(ASN_PATH).get("up", [])
PEERING_PREFIX = args.peering_prefix
assert PEERING_PREFIX in utils.load_json(PREFIX_PATH).get("up", [])

peers_id = args.peers_id
if peers_id is not None:
    for peer_id in peers_id:
        assert peer_id in utils.extract_keyfield_from_peers(utils.get_peers(mux = mux), utils.PeerFields.SESSION_ID)[0]

asn_left = list(set(utils.load_json(ASN_PATH).get("up", [])) - {HIJACKER, VICTIM})

if args.exp_type == 'A':
    if args.type_num <= 0:
        as_path = [HIJACKER]
    else:
        as_path = [HIJACKER] + random.sample(asn_left, args.type_num-1) + [VICTIM]

out_dir = os.path.join(args.out_dir, DIR_TYPE, f'{HIJACKER}-{VICTIM}-type{args.type_num}')
announce_out_dir = os.path.join(out_dir, 'announcement')
withdrawal_out_dir = os.path.join(out_dir, 'withdrawal')
utils.create_dir(announce_out_dir)
utils.create_dir(withdrawal_out_dir)

if args.exp_type == 'A':
    exp_conf = {
        PEERING_PREFIX: {
            "announce": [
                {
                    "muxes": [
                        mux
                    ],
                    "origin": as_path[-1],
                    "prepend": as_path[:-1]
                }
            ]
        }
    }
    if peers_id is not None:
        exp_conf[PEERING_PREFIX]["announce"][0]["peers"] = peers_id
    utils.dump_json(f"{announce_out_dir}/announce_{mux}_{HIJACKER}.json", exp_conf, indent=2)
elif args.exp_type == 'W':
    exp_conf = {
        PEERING_PREFIX: {
            "withdraw": [
                mux
            ]
        }
    }
    utils.dump_json(f"{withdrawal_out_dir}/withdraw_{mux}.json", exp_conf, indent=2)
