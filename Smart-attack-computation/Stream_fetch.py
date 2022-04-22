import pybgpstream
import ujson
import sys

import argparse



parser = argparse.ArgumentParser()

## example usage: python Stream_fetch.py --prefix 184.164.236.0/24 --from "2022-04-14 15:30:00 UTC" --until "2022-04-14 16:00:00 UTC" --type updates
parser.add_argument('--prefix', type=str,  help='prefix to fetch from BGPStream')
parser.add_argument('--from_time',   type=str,  help='fetch records from time')
parser.add_argument('--until_time',  type=str,  help='fetch records until time')
parser.add_argument('--type',   type=str, choices=["ribs", "updates"],  help='type of records to fetch: [ribs, updates]')


args        = parser.parse_args()
record_type = args.type
from_time   = args.from_time
until_time  = args.until_time
prefix      = args.prefix


#record_type = "updates"
#from_time   = "2022-04-14 15:30:00 UTC"
#until_time  = "2022-04-14 16:00:00 UTC"
#from_time    = "2022-04-19 10:17:00 UTC"
#until_time   = "2022-04-19 10:37:00 UTC"
#record_type = "ribs"
#from_time   = "2022-04-14 15:56:00"
#until_time  = "2022-04-14 16:04:00 UTC"


stream = pybgpstream.BGPStream(
    from_time=from_time, until_time=until_time,
    #collectors=["route-views.sg", "route-views.eqix"],
    record_type=record_type,
    filter="prefix exact %s" %args.prefix
)



data_container = list()

for rec in stream.records():
    
    #print(rec)
    #print(dir(rec))

    #print("ok?")
    #print("Received %s record at time %d from collector %s" % (rec.type, rec.time, rec.collector))

    for elem in rec:
        
        # Get the peer ASn
        peer = str(elem.peer_asn)


        #print(elem.fields)
        #print(rec.fields)
        #print(rec)
        #print(elem)


        """
        print_test = "%s|%s|%f|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" %(
        	elem.record_type,
        	elem.type,
        	elem.time,
        	elem.project,
        	elem.collector,
        	elem.router,
        	elem.router_ip,
        	elem.peer_asn,
        	elem.peer_address,
        	elem._maybe_field("prefix"),
        	elem._maybe_field("next-hop"),
        	elem._maybe_field("as-path"),
        	" ".join(elem.fields["communities"]) if "communities" in elem.fields else None,
        	elem._maybe_field("old-state"),
        	elem._maybe_field("new-state")
        )
        """


        elem_data = {
        	"record_type":	elem.record_type,
        	"type": 		elem.type,
        	"time": 		elem.time,
        	"project": 		elem.project,
        	"collector": 	elem.collector,
        	"router": 		elem.router,
        	"router_ip": 	elem.router_ip,
        	"peer_asn": 	elem.peer_asn,
        	"peer_address": elem.peer_address,
        	"prefix": 		elem._maybe_field("prefix"),
        	"next-hop": 	elem._maybe_field("next-hop"),
        	"as-path": 		elem._maybe_field("as-path"),
        	"communities": 	" ".join(elem.fields["communities"]) if "communities" in elem.fields else None,
        	"old-state":	elem._maybe_field("old-state"),
        	"new-state":	elem._maybe_field("new-state")
        }

        data_container.append(elem_data)
        print(elem_data)


    #if len(data_container) >2: break


outfile = "%s-%s.json" %(from_time, record_type)
print("\n>> saving dump to %s" %outfile)
ujson.dump(data_container, open(outfile, "w"), indent = 3)
#ujson.dump(data_container, open("2022-04-14-16:00:00-%s.json" %record_type, "w"), indent = 3)
#ujson.dump(data_container, open("2022-04-19-10:17:00-%s.json" %record_type, "w"), indent = 3)



"""
for elem in stream:
    # record fields can be accessed directly from elem
    # e.g. elem.time
    # or via elem.record
    # e.g. elem.record.time
    print(elem)
    print(dir(elem))
    """