YAML parser will receive a test yaml file as an input. 

A test yaml file should have the following parameters:

* test_id
* start_range
* end_range
* result_duration 
* sessions_per_node
* tool

Start and End range parameters are object sizes for which test will be executed. Sizes can be 
given from bytes, KB, MB up to TB. We can also use KiB format as well. 

Result duration can be specified from seconds up to days. For example, 1d1h, 1h or 2d1h.

Tool can be specified from one of these **s3bench**, **boto3** or **warp**.

