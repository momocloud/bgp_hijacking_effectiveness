import pybgpstream
import pymongo
from enum import Enum

class StreamType(Enum):
    """
    Enum for stream type
    """
    RIB = "ribs"
    UPDATE = "updates"


def collect_db(stream_type:StreamType, prefix: str):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient[stream_type.value]
    mycol = mydb[prefix]

    if stream_type is StreamType.UPDATE:
        mycol.create_index('{"project":1, "collector":1, "peer_asn":1, "second_asn":1, "ori_asn":1, "peer_address":1, "router":1}', 
        name='update_index')

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
        "lastest": True
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
        query_dict = {"project": parsed_dict["project"], "collector": parsed_dict["collector"], "peer_asn": parsed_dict["peer_asn"], "second_asn": parsed_dict["second_asn"],
                    "ori_asn": parsed_dict["ori_asn"], "peer_address": parsed_dict["peer_address"], "router": parsed_dict["router"], "time": { "$gte": parsed_dict["time"]}, "lastest": True}
        if db_collection.count_documents(query_dict) > 0:
            parsed_dict["lastest"] = False
            db_collection.insert_one(parsed_dict)
            print(elem)
        else:
            db_collection.update_many(query_dict, {"$set": {"lastest": False}})
            db_collection.insert_one(parsed_dict)
            print(elem)

def parse_into_db(db_collection: pymongo.collection.Collection, stream: pybgpstream.BGPStream, stream_type: StreamType):
    if stream_type is StreamType.RIB:
        parse_rib_into_db(db_collection, stream)
    elif stream_type is StreamType.UPDATE:
        parse_update_into_db(db_collection, stream)


def main(mycol: pymongo.collection.Collection, stream_type: StreamType, stream: pybgpstream.BGPStream):
    parse_into_db(mycol, stream, stream_type)


if __name__ == '__main__':
    stream_type = StreamType.UPDATE
    prefix = "184.164.236.0/24"
    _, mycol = collect_db(stream_type=stream_type, prefix=prefix)

    stream = pybgpstream.BGPStream(
        from_time="2022-03-29 13:50:00", until_time="2022-03-29 14:00:00 UTC",
        record_type=stream_type.value,
        filter="prefix exact " + prefix
    )

    main(mycol=mycol, stream_type=stream_type, stream=stream)

