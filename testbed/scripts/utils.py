import json
import time
import os
import sys
import subprocess
import re
from netaddr import IPNetwork, IPAddress
from enum import Enum
sys.path.insert(0, '../client')
from peering import AnnouncementController as ACtrl

LOCAL_OPERATE_INTERVAL = 5

BIRD_CFG_DIR = '../client/configs/bird'
BIRD_SOCK = '../client/var/bird.ctl'
SCHEMA_FN = '../client/configs/announcement_schema.json'
PEERS_INFO = './meta_configs/peers.json'

class PeerFields(Enum):
    BGP_MUX = "BGP Mux"
    PEER_ASN = "Peer ASN"
    PEER_IP_ADDRESS = "Peer IP Address"
    IP_VERSION = "IP version"
    SHORT_DESCRIPTION = "Short Description"
    TRANSIT = "Transit"
    ROUTE_SERVER = "Route Server"
    SESSION_ID = "Session ID"

class IPVersion(Enum):
    IPv4 = 'IPv4'
    IPv6 = 'IPv6'

class BGPController():
    def __init__(self) -> None:
        self.bird_cfg_dir = BIRD_CFG_DIR
        self.bird_sock = BIRD_SOCK
        self.schema_fn = SCHEMA_FN
        self.a_ctrl = ACtrl(self.bird_cfg_dir, self.bird_sock, self.schema_fn)
    
    def deploy(self, exp_conf):
        self.a_ctrl.deploy(exp_conf)

def is_valid_prefix(prefix):
    '''
    Check whether the prefix is valid.
    '''
    try:
        IPNetwork(prefix)
        return True
    except:
        return False

def is_valid_ip(ip):
    '''
    Check whether the ip is valid.
    '''
    try:
        IPAddress(ip)
        return True
    except:
        return False

def create_dir(path):
    '''
    Create a directory if it does not exist.
    '''
    if not os.path.isdir(path):
        os.makedirs(path)

def load_json(path):
    '''
    Load a json file.
    '''
    with open(path, 'r') as f:
        return json.load(f)

def dump_json(path, data, indent=None):
    '''
    Dump a json file.
    '''
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent)

def extract_configured_muxes(exp_conf):
    '''
    Extract configured muxes from the experiment configuration.
    '''
    exp_muxes = set()
    for prefix in exp_conf:
        if 'announce' in exp_conf[prefix]:
            for elem in exp_conf[prefix]['announce']:
                if 'muxes' in elem:
                    exp_muxes.update(set(elem['muxes']))
        elif 'withdraw' in exp_conf[prefix]:
            exp_muxes.update(set(exp_conf[prefix]['withdraw']))
    return exp_muxes

def extract_configued_peers(peer_elements, exp_conf):
    '''
    Extract peers of configued muxes from the peer elements.
    '''
    exp_muxes = extract_configured_muxes(exp_conf)
    clean_peer_elements = []
    for elem in peer_elements:
        if elem['BGP Mux'] in exp_muxes:
            clean_peer_elements.append(elem)
    return clean_peer_elements

def organize_peers_by_keyfield(peer_elements, key_field: PeerFields):
    '''
    Organize peers by key field.
    '''
    assert key_field in PeerFields
    keyed_peers = {}
    for peer_element in peer_elements:
        key = peer_element[key_field.value]
        if key not in keyed_peers:
            keyed_peers[key] = []
        keyed_peers[key].append(peer_element)
    return keyed_peers

def extract_vpn_mux_status():
    '''
    Get openvpn status of each tap interface.
    '''
    mux_status = {}
    proc = subprocess.run(
        ['./peering', 'openvpn', 'status'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='../client')
    ascii_stdout = proc.stdout.decode('ascii')
    lines = ascii_stdout.splitlines()
    for line in lines:
        mux_match = re.match('^(\S+)\s+(\S+)\s+(\S+)', line)
        if mux_match:
            mux = mux_match.group(1)
            tap = mux_match.group(2)
            status = mux_match.group(3)
            mux_status[mux] = {
                'tap': tap,
                'status': status
            }
    return mux_status

def get_up_vpn_muxes(vpn_mux_status):
    '''
    Get up vpn muxes.
    '''
    return set([mux for mux in vpn_mux_status if vpn_mux_status[mux]['status'] == 'up'])

def extract_bird_mux_status():
    '''
    Get bird status of each mux.
    '''
    mux_status = {}
    proc = subprocess.run(
        ['./peering', 'bgp', 'status'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='../client')
    ascii_stdout = proc.stdout.decode('ascii')
    lines = ascii_stdout.splitlines()
    for line in lines:
        mux_match = re.match('^(\S+)\s+BGP\s+rtup\s+(\S+)\s+\d+\:\d+\:\d+\s+(\S+)', line)
        if mux_match:
            mux = mux_match.group(1)
            status = mux_match.group(2)
            info = mux_match.group(3)
            mux_status[mux] = {
                'status': status,
                'info': info
            }
    return mux_status

def get_established_bird_muxes(bird_mux_status):
    '''
    Get established bird muxes.
    '''
    return set([mux for mux in bird_mux_status if bird_mux_status[mux]['status'] == 'up' and
                              bird_mux_status[mux]['info'] == 'Established'])

def control_mux_tun(muxes, up=True):
    '''
    Control the openvpn tun interface of muxes.
    '''
    state = 'up'
    if not up:
        state = 'down'
    for mux in muxes:
        proc = subprocess.run(
            ['./peering', 'openvpn', state, mux],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd='../client')
    time.sleep(LOCAL_OPERATE_INTERVAL)

def control_mux_bird(up=True):
    '''
    Control the bird mux.
    '''
    state = 'start'
    if not up:
        state = 'stop'
    proc = subprocess.run(
        ['./peering', 'bgp', state],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd='../client')
    time.sleep(LOCAL_OPERATE_INTERVAL)

def close_client():
    '''
    Close openvpn and bird client, then restart the network manager.
    '''
    muxes = get_up_vpn_muxes(extract_vpn_mux_status())
    control_mux_tun(muxes, up=False)
    control_mux_bird(up=False)
    proc = subprocess.run(
        ['service', 'network-manager', 'restart']
    )
    time.sleep(LOCAL_OPERATE_INTERVAL)

def get_peers(mux: str = None, is_transit: bool = None, session_id: int = None, ip_version: IPVersion = None):
    '''
    Get peers from mux and transit state.
    '''
    peers_list = load_json(PEERS_INFO)
    peers_list_to_return = []
    for peer in peers_list:
        if mux is not None and peer[PeerFields.BGP_MUX.value] != mux:
            continue
        if (is_transit is not None) and ((is_transit and peer[PeerFields.TRANSIT.value] == '✘') or (not is_transit and peer[PeerFields.TRANSIT.value] == '✔')):
            continue
        if session_id is not None and peer[PeerFields.SESSION_ID.value] != str(session_id):
            continue
        if ip_version is not None and peer[PeerFields.IP_VERSION.value] != ip_version.value:
            continue
        peers_list_to_return.append(peer)
    return peers_list_to_return

def extract_keyfield_from_peers(peers, *key_fields: PeerFields):
    '''
    Extract key field from peers.
    '''
    return_tuple = []
    for key_field in key_fields:
        assert key_field in PeerFields
        return_tuple.append([peer[key_field.value] for peer in peers])
    return tuple(return_tuple)


if __name__ == '__main__':
    print(extract_keyfield_from_peers(get_peers(mux = 'ufmg01'), PeerFields.SESSION_ID)[0])