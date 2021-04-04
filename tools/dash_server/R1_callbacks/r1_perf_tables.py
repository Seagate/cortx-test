import pandas as pd

import perfdbAPIs as perf_api

OPERATIONS = ["write", "read"]
STATS = ["Throughput", "Latency", "IOPS"]
COSBENCH_CONFIG = [[1, 1000, 100], [10, 100, 100], [50, 100, 100]]
CB_OBJECTS_SIZES = ["4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB", "256 MB"]
HSBENCH_CONFIG = [[1, 1000, 100], [10, 1000, 100], [50, 5000, 100]]
HB_OBJECTS_SIZES = ["4Kb", "100Kb", "1Mb", "5Mb", "36Mb", "64Mb", "128Mb", "256Mb"]


def keys_exists(element, *keys):
    """Check if *keys (nested) exists in `element` (dict)."""
    if not isinstance(element, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


def round_off(value, base=1):
    """
    Summary: Round off to nearest int

    Input : (number) - number
            (base) - round off to nearest base
    Returns: (int) - rounded off number
    """
    if value < 1:
        return round(value, 2)
    if value < 26:
        return int(value)
    return base * round(value / base)


def get_single_bucket_perf_data(build):
    """Get Single Bucket performance data for executive report"""
    col_names = ["Statistics", "4 KB Object", "256 MB Object"]
    operations = ["Write", "Read"]
    stats = ["Throughput", "Latency"]
    objects_sizes = ["4Kb", "256Mb"]
    data = []
    for operation in operations:
        for stat in stats:
            if stat == "Latency":
                temp_data = [f"{operation} {stat} (MBps)"]
            else:
                temp_data = [f"{operation} {stat} (ms)"]
            for objects_size in objects_sizes:
                query = {'Build': build, 'Name': 'S3bench', 'Object_Size': objects_size,
                         'Operation': operation}
                count = perf_api.count_documents(query)
                db_data = perf_api.find(query)
                if stat == "Latency":
                    if count > 0 and keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(round_off(db_data[0][stat]["Avg"] * 1000))
                    else:
                        temp_data.append("-")
                elif stat == "Throughput":
                    if count > 0 and keys_exists(db_data[0], stat):
                        temp_data.append(round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                else:
                    temp_data.append("-")
            data.extend([temp_data])
    df = pd.DataFrame(data, columns=col_names)
    return df


def get_detailed_s3_bucket_perf(build):
    col_names = ["Statistics", "4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB",
                 "256 MB"]
    operations = ["Write", "Read"]
    stats = ["Throughput", "Latency", "IOPS", "TTFB"]
    objects_sizes = ["4Kb", "100Kb", "1Mb", "5Mb", "36Mb", "64Mb", "128Mb", "256Mb"]
    data = []
    for operation in operations:
        for stat in stats:
            if stat in ["Latency", "TTFB"]:
                temp_data = [f"{operation} {stat} (ms)"]
            elif stat in ["Throughput"]:
                temp_data = [f"{operation} {stat} (MBps)"]
            else:
                temp_data = [f"{operation} {stat}"]
            for obj_size in objects_sizes:
                query = {'Build': build, 'Operation': operation, 'Object_Size': obj_size}
                count = perf_api.count_documents(query)
                db_data = perf_api.find(query)
                if stat in ["Latency", "TTFB"]:
                    if count > 0 and keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(round_off(db_data[0][stat]["Avg"] * 1000))
                    else:
                        temp_data.append("-")
                else:
                    if count > 0 and keys_exists(db_data[0], stat):
                        temp_data.append(round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
            data.extend([temp_data])

    return pd.DataFrame(data, columns=col_names)


def get_metadata_latencies(build):
    """Get metadata latency table data."""
    operations = ["PutObjTag", "GetObjTag", "HeadObj"]
    heading = ["Add / Edit Object Tags", "Read Object Tags", "Read Object Metadata"]
    col_names = ["Operation Latency (ms)", "Response Time"]
    data = []
    for ops, head in zip(operations, heading):
        query = {'Name': 'S3bench', 'Build': build, 'Object_Size': '1Kb', 'Operation': ops}
        count = perf_api.count_documents(query)
        db_data = perf_api.find(query)
        if count > 0 and keys_exists(db_data[0], "Latency", "Avg"):
            data.append([head, db_data[0]['Latency']['Avg'] * 1000])
        else:
            data.append([head, "-"])
    return pd.DataFrame(data, columns=col_names)


def get_cosbench_data(build):
    """Read Cosbench data from DB"""
    data = []
    for configs in COSBENCH_CONFIG:
        for operation in OPERATIONS:
            for stat in STATS:
                temp_data = [f"{operation.capitalize()} {stat}"]
                for obj_size in CB_OBJECTS_SIZES:
                    query = {'Build': build, 'Name': "Cosbench", 'Operation': operation,
                             'Object_Size': obj_size, 'Buckets': configs[0], 'Objects': configs[1],
                             'Sessions': configs[2]}
                    count = perf_api.count_documents(query)
                    db_data = perf_api.find(query)

                    if count > 0 and stat == "Latency" \
                            and keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(round_off(db_data[0][stat]["Avg"]))
                    elif count > 0 and keys_exists(db_data[0], stat):
                        temp_data.append(round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                data.append(temp_data)
    return data


def get_hsbench_data(build):
    """Read Hsbench data from DB"""
    data = []
    for configs in HSBENCH_CONFIG:
        for operation in OPERATIONS:
            for stat in STATS:
                temp_data = [f"{operation.capitalize()} {stat}"]
                for obj_size in HB_OBJECTS_SIZES:
                    query = {'Build': build, 'Name': "Hsbench", 'Operation': operation,
                             'Object_Size': obj_size, 'Buckets': configs[0], 'Objects': configs[1],
                             'Sessions': configs[2]}
                    count = perf_api.count_documents(query)
                    db_data = perf_api.find(query)

                    if count > 0 and keys_exists(db_data[0], stat):
                        temp_data.append(round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                data.append(temp_data)
    return data
