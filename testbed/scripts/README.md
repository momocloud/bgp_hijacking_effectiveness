# Scripts to control client controller

## Generate configurations

The first thing to do is to generate configurations used to control client controller in one experiment. The two scripts are [pair](./generate_mux_pair_configurations.py) and [single](./generate_single_mux_configurations.py). Basicly if you want to generate configurations for one hijacking attack, you need to run [pair](./generate_mux_pair_configurations.py) script. Each script has several parameters to be set. You may focus on:

* -j: Hijacker ASN
* -v: Victim ASN
* -p: Announcement prefix
* -t: Type of generation. For announcement use 'A', for withdrawal use 'W'. Basicly, one complete experiment needs both.
* -n: Number of hijacking type.

Here is an example of generate such experiment situation:

| HIJACKER | VICTIM | PREFIX           | NUMBER OF HIJACKING |
| -------- | ------ | ---------------- | ------------------- |
| 263842   | 61576  | 184.164.236.0/24 | 3                   |

```python
python3 generate_mux_pair_configurations.py -j 263842 -v 61576 -p 184.164.236.0/24 -t A -n 3
python3 generate_mux_pair_configurations.py -j 263842 -v 61576 -p 184.164.236.0/24 -t W -n 3
```

Note that in the script, we cannot control the muxes. If you want to control the muxes, you need to edit the [metafile](./meta_configs/valid_muxes.json) to control which muxes are used. It will generate several pairs of up muxes. If you want to apply one exact experiment, set two up muxes and let victim in the first mux, and hijacker in the second mux.

For such mux configuration,

```json
{ "up": ["wisc01", "grnet01"],
  "down": ["..."]
}
```

you can run

```python
python3 generate_mux_pair_configurations.py -j 263842 -v 61576 -p 184.164.236.0/24 -t A -n 3
python3 generate_mux_pair_configurations.py -j 263842 -v 61576 -p 184.164.236.0/24 -t W -n 3
```

to get:
```txt
├── exp_confs
│   └── pair
│       └── h_grnet01-v_wisc01
│           └── h_263842-v_61576
│               └── type3
│                   ├── announcement
│                   │   ├── announce_hijacker_grnet01.json
│                   │   └── announce_victim_wisc01.json
│                   └── withdrawal
│                       └── withdraw_wisc01_grnet01.json
```
