"""
Schemas to be used in backend of the dashboard
"""

def get_common_schema(data):
    entry = {
        'Branch': data['branch'],
        'Count_of_Servers': data['nodes'],
        'Percentage_full': data['pfull'],
        'Iteration': data['itrns'],
        'Custom': data['custom'], 
        'Buckets': data['buckets'],
        'Sessions': data['sessions']
    }
    return entry


def get_statistics_schema(data):
    entry = get_common_schema(data)
    entry['Build'] = data['build']

    return entry


def get_complete_schema(data):
    entry = get_common_schema(data)
    entry['Build'] = data['build']
    entry['Object_Size'] = data['objsize']
    entry['Operation'] = data['operation']

    return entry
  
'''
        'Count_of_Clients': data['clients'],
'''

statistics_column_headings = ['Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)', 'Write TTFB (ms)',
                              'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)', 'Read TTFB (ms)']

multiple_buckets_headings = ['Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)',
                             'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)']

bucketops_headings = ['Create Buckets (BINIT)', 'Put Objects (PUT)', 'Listing Objects (LIST)', 'Get Objects (GET)',
                      'Delete Objects (DEL)', 'Clear Buckets (BCLR)', 'Delete Buckets (BDEL)']


def get_dropdown_labels(dropdown_type):
    mapping = {
        'nodes' : ' Nodes',
        'pfill' : '% Utilization',
        'itrns' : ' Iteration',
        'buckets' : ' Bucket(s)',
        'sessions' : ' Session(s)'
    }

    return mapping[dropdown_type]