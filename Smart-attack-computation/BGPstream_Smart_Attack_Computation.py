from collections import defaultdict
import numpy as np
import argparse
import ujson
import sys

from math import inf as INFINIT
from pprint import pprint




"""
Input: A file containing all updated fetched within a time period from BGPstream (See below record example).
{
  "record_type": "rib",
  "type": "R",
  "time": 1649952000.0,
  "project": "ris",
  "collector": "rrc19",
  "router": null,
  "router_ip": null,
  "peer_asn": 37271,
  "peer_address": "197.157.79.173",
  "prefix": "184.164.236.0\/24",
  "next-hop": "197.157.79.173",
  "as-path": "37271 2914 7018 3128 3128 3128 47065 61576",
  "communities": "2914:3000 37271:5103 37271:5100 2914:2000 2914:1009 2914:420 37271:5002",
  "old-state": null,
  "new-state": null
}


Output: A dictionary containing all observed AS-paths per project -> collector -> peer_asn -> peer_adress.
        Container format: project -> collector -> peer_asn -> peer_adress =  [as-path, ..., as-path]

"""



def read_BGPstream_file(filename):

    filedata = ujson.load(open(filename))

    ## Container format: Four dictionaries back to back. Value: List of all AS-paths observed by BGPStream per peer_adress. 
    ## collector -> peer_asn -> peer_adress =  [as-path, ..., as-path]
    container_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list))) #collector -> peer_asn -> peer_adress =  [as-path., ... ] 

    for record in filedata:
        project     = record["project"]
        collector   = record["collector"]
        peer_adress = record["peer_address"]
        peer_asn    = record["peer_asn"]
        AS_path     = record["as-path"]         ## Value = None if not available (e.g., case Withdraws)
        record_type = record["type"]            ## Type A: announcement, W: withdraw, U: unknown

        print("peer_address: %s, peer_asn: %s, AS-path: %s" %(peer_adress, peer_asn, AS_path))

        ## sanity check: peer_adress is not empty 
        assert(peer_adress)

        ## Verifies that only W records do not possess a path
        if not AS_path and record_type != "W":
            print(record)
            sys.exit()

        container_dict[collector][peer_asn][peer_adress].append(AS_path)


    return container_dict



"""
Computes the proximity of each monitor as the length of the reported AS-path length 

Input: 
  a) Reported paths per monitor to route collectors. Format: collector -> peer_asn -> peer_IP = [as-path, ..., as-path]
  b) proximity_type: how to compute the proximity (from the last or the longest reported AS path)

Output:
  a) Proximity to each monitor: format dict, Keys: "collector-peer_asn-peer_IP", Values: AS path length

"""
def compute_monitor_proximity(reported_paths_container, proximity_type="latest-path"):
    proximity_dict = dict()

    for collector, peer_asn_dict in reported_paths_container.items():
        for peer_asn, peer_addr_dict in peer_asn_dict.items():
            for peer_addr, AS_path_list in peer_addr_dict.items():

                ## simplify data structure: compute a unified key
                dict_key = "%s-%s-%s" %(collector, peer_asn, peer_addr)

                ## compute the proximity from the latest, i.e. the last, reported AS path
                ## Note: make sure the selected path is not None (indicating a withdraw)
                ## Note: In the awkward scenario where only withdraws exist, Then Skip
                if proximity_type == "latest-path":
                    filtered_AS_path = [ path for path in AS_path_list if path is not None]
                    if filtered_AS_path:
                      proximity_dict[dict_key] = len(filtered_AS_path[-1])

                ## compute as proximity the one of the longest reported AS path
                if proximity_type == "longest-path":
                  proximity_dict[dict_key] = len(max(AS_path_list, key=len))

    return proximity_dict



"""
Input: 
  a) Proximity dict of monitors to the victim
  b) proximity dict of monitors to the hijacker

Output:
  a) Proximity difference of each monitor M: Hijacker_best_path_length_M - victim_best_path_length_M

"""
def compute_proximity_difference(proximity_V, proximity_H):
  prox_diff = dict()

  ## Union of the keys of the two proximity dicts
  combined_keys = set.union( set(proximity_V.keys()), set(proximity_H.keys()) )

  for key in combined_keys:
      #print(proximity_H[key])
      #print(proximity_V)

      if key in proximity_V and key in proximity_H:       prox_diff[key] = proximity_H[key] - proximity_V[key]
      elif key not in proximity_V and key in proximity_H: prox_diff[key] = proximity_H[key] - INFINIT
      elif key in proximity_V and key not in proximity_H: prox_diff[key] = INFINIT - proximity_V[key]
      else: assert(False), "Bug: impossible condition"

  return prox_diff



## To do
def compute_smart_attack(proximity_diff):
    
    print(">> Printing computed monitor proximities (in ascending order)")
    for monitor, prox_HV in sorted(proximity_diff.items(), key=lambda item: item[1]):
        print("%s, %s" %(monitor, prox_HV))

    ## Monitors with negative proximities are safe.
    ## Monitors with positive proximities need to be handled.







if __name__ == "__main__":


  #V_BGPstream_files = ["2022-04-14-16:00:00-updates.json"]  ## Victim   prefix paths fetched from BGPStream (single file)
  #H_BGPstream_files = ["2022-04-19-10:17:00-updates.json"]  ## Hijacker prefix paths fetched from BGPStream (one file for each announced prefix per hijacker neighbor)
  #H_neighbor_ASNs   = ["dummy_nbor"]                        ## The corresponding Hijacker neighbors.

  ## sanity checks
  #assert(len(H_BGPstream_files) == len(H_neighbor_ASNs))

  #container_V = read_BGPstream_file(V_BGPstream_files[0])



  parser = argparse.ArgumentParser()

  ## example usage: python BGPstream_Smart_Attack_Computation.py -V 2022-04-14-16:00:00-updates.json -H 2022-04-19-10:17:00-updates.json
  parser.add_argument('-V', '--Victim', type=str,  help='Victim path file to read from (fetched from BGPStream)')
  parser.add_argument('-H', '--Hijacker', nargs='*', type=str, help='Hijacker path files to read from (comma separated, one file for each announced prefix per hijacker neighbor)')


  args    = parser.parse_args()
  file_V  = args.Victim
  files_H = args.Hijacker


  container_V = read_BGPstream_file(file_V)

  #for BGPstream_file_H, neighbor_H in zip(H_BGPstream_files, H_neighbor_ASNs):
  for BGPstream_file_H in files_H:
      container_H = read_BGPstream_file(BGPstream_file_H)

      ## compute proximity of each monitor to the victim
      ## compute proximity of each monitor to the hijacker
      prox_V = compute_monitor_proximity(container_V)
      prox_H = compute_monitor_proximity(container_H)

      pprint(prox_V)
      pprint(prox_H)

      ## Compute the proximity different of each monitor to the hijacker versus the victim. 
      ## Prox_M: len(Hijacker_best_path_M) - len(victim_best_path_M)
      prox_diff = compute_proximity_difference(prox_V, prox_H)

      ## calculate the smart attack type to announce from the two proximities
      compute_smart_attack(prox_diff)







 


