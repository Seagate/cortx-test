from pathlib import Path
import os
print(os.path.exists('cortx-test/config/common_config.yaml'))
print(Path(__file__).parent.parent)
print(os.path.exists(os.path.join(Path(__file__).parent.parent,'config/common_config.yaml')))
from commons.params import COMMON_CONFIG, CSM_CONFIG, S3_CONFIG
print(COMMON_CONFIG, CSM_CONFIG, S3_CONFIG)