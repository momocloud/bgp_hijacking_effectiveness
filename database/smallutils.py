def get_time_gap_from_records(record_str):
    records_l = record_str.split('\n')
    time_list = list()

    start = None
    end = None

    for record in records_l:
        if 'announce' in record and start is None:
            start = record.split('|')[1]
        if 'withdraw' in record and start is not None:
            end = record.split('|')[1]
            time_list.append((int(start), int(end)))
            start, end = None, None
            
    print(time_list)
    
    return time_list

# records = '''
# 2022-08-03 14:16:21.221246|1659536181|{"184.164.236.0/24": {"announce": [{"muxes": ["wisc01"], "origin": 61576, "prepend": [61576, 61576]}]}}
# 2022-08-03 14:16:21.370430|1659536181|{"184.164.237.0/24": {"announce": [{"muxes": ["grnet01"], "origin": 61575}]}}
# 2022-08-03 15:06:21.622219|1659539181|{"184.164.237.0/24": {"withdraw": ["grnet01"]}}
# 2022-08-03 15:06:21.740988|1659539181|{"184.164.236.0/24": {"withdraw": ["wisc01"]}}
# '''


# print(get_time_gap_from_records(records))