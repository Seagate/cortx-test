YAML parser will receive a test yaml file as an input. 

A test yaml file should have the following parameters:

* test_id
* object_size
* part_size
* result_duration
* sessions_per_node
* sessions
* tool

object_size & part_size can be given as range for s3bench tests, so those can have the following keys in it.
* start
* end

Start and End range parameters are object/part sizes for which test will be executed.
Sizes can be given from bytes, KB, MB up to TB. We can also use KiB format as well. 

Result duration can be specified from seconds up to days. For example, 1d1h, 1h or 2d1h.

Tool can be specified from one of these **s3bench**, **s3api** or **warp**.

