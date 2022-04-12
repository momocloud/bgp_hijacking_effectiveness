import utils
from pprint import pprint
import sys
import time
sys.path.insert(0, '../client')

ANNOUNCE_COOLING_TIME = 600

class Experiment():
    def __init__(self, *exp_confs):
        self.announce_exp_confs_vic = [utils.load_json(conf) for conf in exp_confs if 'announce' in conf and 'victim' in conf]
        self.announce_exp_confs_hij = [utils.load_json(conf) for conf in exp_confs if 'announce' in conf and 'hijacker' in conf]
        self.withdraw_exp_confs = [utils.load_json(conf) for conf in exp_confs if 'withdraw' in conf]
        self.muxes = set()
        self.controller = utils.BGPController()
        self.deploy_timestamp = dict()
        self._init()

    def _init(self):
        '''
        Get all the muxes needed.
        '''
        for conf in self.announce_exp_confs_vic + self.announce_exp_confs_hij + self.withdraw_exp_confs:
            self.muxes |= utils.extract_configured_muxes(conf)

    def _open_client(self):
        '''
        Open the mux tunnel and bird if necessary.
        '''
        up_muxes = utils.get_up_vpn_muxes(utils.extract_vpn_mux_status())
        if len(self.muxes-up_muxes) != 0:
            print('Need to open client!')
            utils.control_mux_tun(self.muxes, True)
            utils.control_mux_bird(True)
            pprint(f'Up muxes: {utils.get_up_vpn_muxes(utils.extract_vpn_mux_status())}')
            time.sleep(5)
            pprint(f'Established birds: {utils.get_established_bird_muxes(utils.extract_bird_mux_status())}')
        
    def _deploy_one_conf(self, conf):
        self._open_client()
        self.controller.deploy(conf)
        self.deploy_timestamp.setdefault(str(conf), int(time.time()))
        time.sleep(ANNOUNCE_COOLING_TIME)

    def deploy_victim_announcement(self):
        '''
        Deploy the victims' announements.
        '''
        for conf in self.announce_exp_confs_vic:
            print(f'Deploying victim announcement {conf}...')
            self._deploy_one_conf(conf)
    
    def deploy_hijacker_announcement(self):
        '''
        Deploy the hijacker's announcements.
        '''
        for conf in self.announce_exp_confs_hij:
            print(f'Deploying hijacking announcement {conf}...')
            self._deploy_one_conf(conf)
        
    def deploy_all_announcement(self):
        '''
        Deploy all announcements.
        '''
        self.deploy_victim_announcement()
        self.deploy_hijacker_announcement()

    def deploy_withdrawal(self):
        '''
        Deploy withdrawals.
        '''
        for conf in self.withdraw_exp_confs:
            print(f'Deploying withdrawal {conf}...')
            self._deploy_one_conf(conf)

    def close(self):
        '''
        Close the mux tunnel and bird.
        '''
        print('Closing the client...')
        utils.close_client()
        print('Close finished!')