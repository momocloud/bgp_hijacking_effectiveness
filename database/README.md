# About data format stored into database

## How to config the environment

Because in this project we need to use [PyBGPStream](https://bgpstream.caida.org/docs/install/pybgpstream) to get data from BGPStream, we have to run python files in Linux environment since PyBGPStream can be only run in Linux. Besides, we use [MongoDB (community edition 5.0)](https://www.mongodb.com/) to store the data (ribs and updates). So basicly, we need a Linux environment running Python (>=3.5) and connectable MongoDB environment.

Right now we have two ways to config it. One way is to run all in one Linux environment like a virtual machine. The other way is to run MongoDB in Windows and run Python in [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/).

### Run all in Linux environment

For MongoDB, you can try the [offical guide](https://www.mongodb.com/docs/manual/administration/install-on-linux/) to install it for your distribution.

After installing it, start mongod service before running the scripts. For we are using Ubuntu 20Lts, mongod can be started by running such command.

```bash
sudo service mongod start
```

Besides, if your want to connect it from other machines (like from physical machine to virtual machine), you should change the IP setting from 127.0.0.1/localhost to 0.0.0.0 in the `net` part of configuation file written in the offical guide. For Ubuntu 20, you can check [here](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/#:~:text=to%20these%20directories.-,Configuration%20File,-The%20official%20MongoDB) to find how to edit that file.

### Run in Windows with WSL 1

For MongoDB, you can try the [offical guide](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/) to install it. Basicly, it is to download a [msi installer](https://www.mongodb.com/try/download/community?tck=docs_server) and install it locally.

After installing it, start MongoDB service before running the scripts. Use following command to start or stop MongoDB in your windows shell as administrator.

```powershell
net start MongoDB  // start MongoDB
net stop MongoDB   // stop MongoDB
```

Because we still need virtual machine to run peering testbed scripts, so we use WSL 1 instead of WSL 2. And since WSL 1 can directly get access to Windows, so we don't need to edit the net configuration for MongoDB in Windows.

For WSL, we use version 1 since we don't want to use hyper-v. You can try this [documentation](https://www.ridom.de/seqsphere/u/Windows_Subsystem_For_Linux.html) to install it. Then you can install the Python and Python modules needed like in one Linux system.

### Required python version and modules

1. Python (>=3.5)

2. [PyBGPStream](https://github.com/caida/pybgpstream)

3. [PyMongo](https://pymongo.readthedocs.io/en/stable/)