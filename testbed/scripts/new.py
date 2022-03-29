import utils
from pprint import pprint
import sys
sys.path.insert(0, '../client')

# exp_conf = utils.load_json('/home/kun/BGP_HV/testbed/scripts/exp_confs/announcement/single/announce_amsterdam01_61575.json')
# muxes = utils.extract_configured_muxes(exp_conf)
# utils.control_mux_tun(muxes, True)
# pprint(utils.get_up_vpn_muxes(utils.extract_vpn_mux_status()))
# utils.control_mux_bird(True)
# pprint(utils.get_established_bird_muxes(utils.extract_bird_mux_status()))

# controller = utils.BGPController()
# controller.deploy(exp_conf)
# 50 15:55 60

utils.close_client()