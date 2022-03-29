# About data format stored into database

## Before we use it

We use [MongoDB](https://www.mongodb.com/) to store the data (ribs and updates). Community edition 5.0 is used in this project. You can try the offical guide [here](https://www.mongodb.com/docs/manual/administration/install-community/) to install it.

After installing it, start mongod before running the scripts. For we are using Ubuntu 20Lts, mongod can be started by running such command.

```bash
sudo service mongod start
```

Besides, if your want to connect it from other machine (like from physical machine to virtual machine), you should change the IP setting to 0.0.0.0 in the `net` part of configuation file written in the offical guide. For Ubuntu 20, you can check [here](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/#:~:text=to%20these%20directories.-,Configuration%20File,-The%20official%20MongoDB) to edit that file.

Meanwhile, [pymongo](https://pypi.org/project/pymongo/) is also used in the scripts to operate the database.