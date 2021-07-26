from Performance.schemas import statistics_column_headings, multiple_buckets_headings
from threading import Thread
import pandas as pd
from Performance.schemas import get_statistics_schema, get_complete_schema
from Performance.global_functions import get_distinct_keys, sort_object_sizes_list, get_db_details, keys_exists, round_off
from Performance.mongodb_api import find_documents, count_documents
from Performance.styles import dict_style_header, dict_style_cell
import dash_table
import dash_html_components as html

def get_average_data(count, data, stat, subparam, multiplier):
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat][subparam] * multiplier)
    else:
        return "NA"


def get_data(count, data, stat, multiplier):
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat] * multiplier)
    else:
        return "NA"


def get_data_from_database(data_needed_for_query):
    query = get_statistics_schema(data_needed_for_query)
    objects = get_distinct_keys(data_needed_for_query['release'], 'Object_Size', query)
    objects = sort_object_sizes_list(objects)
    threads = []
    if data_needed_for_query['Name'] == 'S3bench':
        results = {
            'Object Sizes': statistics_column_headings
        }
    else:
        results = {
            'Object Sizes' : multiple_buckets_headings
        }


    for obj in objects:  
        get_benchmark_data(data_needed_for_query, results, obj)    
        # temp = Thread(target=get_benchmark_data, args=(data_needed_for_query, results, obj))
        # temp.start()
        # threads.append(temp)

    # for thread in threads:
    #     thread.join()


    df = pd.DataFrame(results)
    df = df.T
    df.reset_index(inplace=True)
    df.columns = df.iloc[0]
    df = df[1:]

    return df


def get_benchmark_data(data_needed_for_query, results, obj):
    temp_data = []
    operations = ["Write", "Read"]
    if data_needed_for_query["Name"] == 'S3bench':
        stats = ["Throughput", "IOPS", "Latency", "TTFB"]
    else:
        stats = ["Throughput", "IOPS", "Latency"]

    uri, db_name, db_collection = get_db_details(data_needed_for_query['release'])

    for operation in operations:
        data_needed_for_query['operation'] = operation
        data_needed_for_query['objsize'] = obj
        query = get_complete_schema(data_needed_for_query)
        count = count_documents(query=query, uri=uri, db_name=db_name,
                            collection=db_collection)
        db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                collection=db_collection)

        for stat in stats:
            if data_needed_for_query["Name"] == 'S3bench':
                if stat in ["Latency", "TTFB"]:
                    temp_data.append(get_average_data(count, db_data, stat, "Avg", 1000))
                else:
                    temp_data.append(get_data(count, db_data, stat, 1))
            else:
                try:
                    temp_data.append(get_data(count, db_data, stat, 1))
                except TypeError:
                    temp_data.append(get_average_data(count, db_data, stat, "Avg", 1))

    results[obj] = temp_data


def get_dash_table_from_dataframe(df, bench, column_id):
    if bench == 'metadata_s3bench':
        headings = [{'name': 'Operations', 'id': 'Statistics'},
                    {'name': 'Latency (ms)', 'id': '1KB'}
                    ]
    else:
        headings = [
                {'name': column, 'id': column} for column in list(df.columns)
        ]

    benchmark = dash_table.DataTable(
        id=f"{bench}_table",
        columns=headings,
        data=df.to_dict('records'),
        merge_duplicate_headers=True,
        sort_action="native",
        style_header=dict_style_header,
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#E5E4E2'},
            {'if': {'column_id': column_id}, 'backgroundColor': '#D8D8D8'}
        ],
        style_cell=dict_style_cell
    )
    return benchmark


def get_workload_headings(data):
    return html.H5(f"Data for {data['build']} build on branch {data['branch']} with {data['nodes']} nodes, {data['pfull']}% utilization having workload of {data['buckets']} buckets and {data['sessions']} sessions.")


def get_metadata_latencies(data_needed_for_query):
    objects = ['1KB']

    results = {
            'Statistics': ['Add / Edit Object Tags', 'Read Object Tags',
                           'Read Object Metadata']
    }
    for obj in objects:  
        temp_data = []
        operations = ["PutObjTag", "GetObjTag", "HeadObj"]  

        uri, db_name, db_collection = get_db_details(data_needed_for_query['release'])

        for operation in operations:
            data_needed_for_query['operation'] = operation
            data_needed_for_query['objsize'] = obj
            query = get_complete_schema(data_needed_for_query)
            count = count_documents(query=query, uri=uri, db_name=db_name,
                                collection=db_collection)
            db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                    collection=db_collection)
            
            temp_data.append(get_average_data(count, db_data, "Latency", "Avg", 1000))

        results[obj] = temp_data

    df = pd.DataFrame(results)
    return df