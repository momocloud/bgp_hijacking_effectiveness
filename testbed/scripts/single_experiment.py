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
        self.announce_exp_confs_bas = [utils.load_json(conf) for conf in exp_confs if 'announce' in conf and 'base' in conf]
        self.announce_exp_confs_oth = [utils.load_json(conf) for conf in exp_confs if 'announce' in conf and 'hijacker' not in conf and 'victim' not in conf and 'base' not in conf]
        self.withdraw_exp_confs_bas = [utils.load_json(conf) for conf in exp_confs if 'withdraw' in conf and 'base' in conf]
        self.withdraw_exp_confs_nob = [utils.load_json(conf) for conf in exp_confs if 'withdraw' in conf and 'base' not in conf]
        self.muxes = set()
        self.controller = utils.BGPController()
        self.deploy_timestamp = dict()
        self._init()

    def _init(self):
        '''
        Get all the muxes needed.
        '''
        for conf in self.announce_exp_confs_vic + self.announce_exp_confs_hij + self.announce_exp_confs_bas + self.announce_exp_confs_oth:
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
            time.sleep(10)
        
    def _deploy_one_conf(self, conf, cooling_time):
        self._open_client()
        self.controller.deploy(conf)
        self.deploy_timestamp.setdefault(str(conf), int(time.time()))
        time.sleep(cooling_time)

    def deploy_victim_announcement(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy the victims' announements.
        '''
        for conf in self.announce_exp_confs_vic:
            print(f'Deploying victim announcement {conf}...')
            self._deploy_one_conf(conf, cooling_time)
    
    def deploy_hijacker_announcement(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy the hijacker's hijacking announcements.
        '''
        for conf in self.announce_exp_confs_hij:
            print(f'Deploying hijacking announcement {conf}...')
            self._deploy_one_conf(conf, cooling_time)

    def deploy_base_announcement(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy hijacker's base announcements.
        '''
        for conf in self.announce_exp_confs_bas:
            print(f'Deploying hijacker\'s base announcement {conf}...')
            self._deploy_one_conf(conf, cooling_time)
 
    def deploy_other_announcement(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy announcements neithor hijackers nor victim.
        '''
        for conf in self.announce_exp_confs_oth:
            print(f'Deploying other announcement {conf}...')
            self._deploy_one_conf(conf, cooling_time)
        
    def deploy_all_announcement(self, wait_time=600):
        '''
        Deploy all announcements.
        '''
        if self.announce_exp_confs_vic:
            self.deploy_victim_announcement(cooling_time=0)
        if self.announce_exp_confs_bas:
            self.deploy_base_announcement()
            time.sleep(wait_time)
        if self.announce_exp_confs_hij:
            self.deploy_hijacker_announcement()
            time.sleep(wait_time)
        if self.announce_exp_confs_oth:
            self.deploy_other_announcement()

    def deploy_base_withdrawal(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy withdrawals which is base announcement.
        '''
        for conf in self.withdraw_exp_confs_bas:
            print(f'Deploying base withdrawal {conf}...')
            self._deploy_one_conf(conf, cooling_time)

    def deploy_nonbase_withdrawal(self, cooling_time=ANNOUNCE_COOLING_TIME):
        '''
        Deploy withdrawals which is base announcement.
        '''
        for conf in self.withdraw_exp_confs_nob:
            print(f'Deploying nonbase withdrawal {conf}...')
            self._deploy_one_conf(conf, cooling_time)

    def deploy_all_withdrawal(self):
        '''
        Deploy all withdrawals.
        '''
        self.deploy_base_withdrawal(cooling_time=0)
        self.deploy_nonbase_withdrawal(cooling_time=0)

    def close(self):
        '''
        Close the mux tunnel and bird.
        '''
        print('Closing the client...')
        utils.close_client()
        print('Close finished!')