from single_experiment import Experiment
import os
import time
import json

confs = list()
for r, _, fs in os.walk('exp_confs'):
    for f in fs:
        if f.endswith('.json'):
            confs.append(os.path.join(r, f))
            print(f'Detect conf: {os.path.join(r, f)}')

exp = Experiment(*confs)

exp.deploy_announcement()
time.sleep(1500)
exp.deploy_withdrawal()
time.sleep(1500)
exp.close()

with open('./testtime.json', 'w') as f:
    json.dump(exp.deploy_timestamp, f)