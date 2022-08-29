import pybgpstream
import pymongo
from enum import Enum

class StreamType(Enum):
    """
    Enum for stream type
    """
    RIB = "ribs"
    UPDATE = "updates"


def collect_db(stream_type:StreamType, prefix: str, name=None, continuation=False):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient[stream_type.value]
    if name is None:
        name = prefix
    
    if not continuation:
        if name in mydb.list_collection_names():
            mydb.drop_collection(name)

    mycol = mydb[name]

    return mydb, mycol

def parse_to_dict(elem: pybgpstream.pybgpstream.BGPElem):
    returned_dict = {
        "project": elem.project,
        "collector": elem.collector,
        "time": int(elem.time),
        "peer_asn": elem.peer_asn,
        "second_asn": None,
        "ori_asn": None,
        "peer_address": elem.peer_address,
        "router": elem.router,
        "as_path": None,
        "latest": True
    }

    if elem._maybe_field("as-path") is not None:
        returned_dict["as_path"] = elem._maybe_field("as-path").split(" ")
    if elem._maybe_field("as-path") is None:
        returned_dict["as_path"] = []
    else:
        returned_dict["as_path"] = elem._maybe_field("as-path").split(" ")
        if len(returned_dict["as_path"]) > 2:
            returned_dict["second_asn"] = returned_dict["as_path"][1]
        returned_dict["ori_asn"] = returned_dict["as_path"][-1]

    return returned_dict

def parse_rib_into_db(db_collection: pymongo.collection.Collection, stream: pybgpstream.BGPStream):
    counter = 0
    parsed_list = []
    for elem in stream:
        if counter >= 50:
            db_collection.insert_many(parsed_list)
            counter = 0
            parsed_list = []
        parsed_list.append(parse_to_dict(elem))
        counter += 1
        print(elem)
    if parsed_list:
        db_collection.insert_many(parsed_list)

def parse_update_into_db(db_collection: pymongo.collection.Collection, stream: pybgpstream.BGPStream):
    for elem in stream:
        parsed_dict = parse_to_dict(elem)
        # query_dict_gt = {"project": parsed_dict["project"], "collector": parsed_dict["collector"], "peer_asn": parsed_dict["peer_asn"], "second_asn": parsed_dict["second_asn"],
        #             "ori_asn": parsed_dict["ori_asn"], "peer_address": parsed_dict["peer_address"], "router": parsed_dict["router"], "time": { "$gt": parsed_dict["time"]}, "latest": True}
        query_dict_gt = {"project": parsed_dict["project"], "collector": parsed_dict["collector"], "peer_asn": parsed_dict["peer_asn"],
                    "ori_asn": parsed_dict["ori_asn"], "peer_address": parsed_dict["peer_address"], "router": parsed_dict["router"], "time": { "$gt": parsed_dict["time"]}, "latest": True}
        if db_collection.count_documents(query_dict_gt) > 0:
            parsed_dict["latest"] = False
            db_collection.insert_one(parsed_dict)
            print(elem)
        else:
            # query_dict_lte = {"project": parsed_dict["project"], "collector": parsed_dict["collector"], "peer_asn": parsed_dict["peer_asn"], "second_asn": parsed_dict["second_asn"],
            #         "ori_asn": parsed_dict["ori_asn"], "peer_address": parsed_dict["peer_address"], "router": parsed_dict["router"], "time": { "$lte": parsed_dict["time"]}, "latest": True}
            query_dict_lte = {"project": parsed_dict["project"], "collector": parsed_dict["collector"], "peer_asn": parsed_dict["peer_asn"],
                    "ori_asn": parsed_dict["ori_asn"], "peer_address": parsed_dict["peer_address"], "router": parsed_dict["router"], "time": { "$lte": parsed_dict["time"]}, "latest": True}
            db_collection.update_many(query_dict_lte, {"$set": {"latest": False}})
            db_collection.insert_one(parsed_dict)
            print(elem)

def parse_into_db(db_collection: pymongo.collection.Collection, stream: pybgpstream.BGPStream, stream_type: StreamType):
    if stream_type is StreamType.RIB:
        parse_rib_into_db(db_collection, stream)
    elif stream_type is StreamType.UPDATE:
        parse_update_into_db(db_collection, stream)


def main(mycol: pymongo.collection.Collection, stream_type: StreamType, stream: pybgpstream.BGPStream):
    parse_into_db(mycol, stream, stream_type)


# if __name__ == '__main__':
#     stream_type = StreamType.UPDATE
#     prefix = "184.164.237.0/24"
#     _, mycol = collect_db(stream_type=stream_type, prefix=prefix, name="184.164.237.0/24_b-39")

#     stream = pybgpstream.BGPStream(
#         from_time=1656093665, until_time=1656096666,
#         record_type=stream_type.value,
#         filter="prefix exact " + prefix
#     )

#     main(mycol=mycol, stream_type=stream_type, stream=stream)

