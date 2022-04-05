import utils
from pprint import pprint
import sys
import time
sys.path.insert(0, '../client')


class Experiment():
    def __init__(self, *exp_confs):
        self.announce_exp_confs = [conf for conf in exp_confs if 'announce' in conf]
        self.withdraw_exp_confs = [conf for conf in exp_confs if 'withdraw' in conf]
        self.muxes = set()
        self.controller = utils.BGPController()
        self.deploy_timestamp = dict()
        self._init()

    def _init(self):
        '''
        Get all the muxes needed.
        '''
        for conf in self.announce_exp_confs + self.withdraw_exp_confs:
            self.muxes |= utils.extract_configured_muxes(conf)

    def _open_client(self):
        '''
        Open the mux tunnel and bird if necessary.
        '''
        print('Need to open client!')
        utils.control_mux_tun(self.muxes, True)
        utils.control_mux_bird(True)
        pprint(f'Up muxes: {utils.get_up_vpn_muxes(utils.extract_vpn_mux_status())}')
        pprint(f'Established birds: {utils.get_established_bird_muxes(utils.extract_bird_mux_status())}')


    def deploy_announcement(self):
        '''
        Deploy announcement.
        '''
        up_muxes = utils.get_up_vpn_muxes(utils.extract_vpn_mux_status())
        if len(self.muxes-up_muxes) != 0:
            self._open_client()
        for conf in self.announce_exp_confs:
            print(f'Deploying announcement {conf}...')
            self.controller.deploy(conf)
            self.deploy_timestamp.setdefault(conf, time.time())

    def deploy_withdrawal(self):
        '''
        Deploy withdrawal.
        '''
        up_muxes = utils.get_up_vpn_muxes(utils.extract_vpn_mux_status())
        if len(self.muxes-up_muxes) != 0:
            self._open_client()
        for conf in self.withdraw_exp_confs:
            print(f'Deploying withdrawal {conf}...')
            self.controller.deploy(conf)
            self.deploy_timestamp.setdefault(conf, time.time())

    def close(self):
        '''
        Close the mux tunnel and bird.
        '''
        utils.close_client()