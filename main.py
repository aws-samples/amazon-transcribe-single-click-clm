import sys, boto3, logging

from orchestrator.orchestrator import Orchestrator

logger = logging.getLogger()
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(u'%(asctime)s :: %(levelname)s :: %(message)s'))
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)

# Reads config file
from config import (
    BUCKET_PATH,
    CLM,
    ACCESS
)

# main method reads config file, sets a few other parameters, 
# and calls the Orchestrator object
if __name__ == "__main__":
    # read input from config file
    bucket = BUCKET_PATH["bucket"]
    
    # bucket_prefix is the starting folder under which user uploads input files
    bucket_prefix = BUCKET_PATH["bucket_prefix"]
    # adding "/" if user didn't enter it in config file
    if bucket_prefix[-1] != "/": bucket_prefix = bucket_prefix + "/"
        
    # keywords_prefix is the folder under which user uploads initial keywords file if they have one (optional input)
    keywords_prefix = bucket_prefix + "keywords/"
    
    # data_prefix is an internal folder used by this framework to store it downloads from Wikipedia
    data_prefix = bucket_prefix + "training_data/"
    
    # output_prefix is an internal folder under which this framework stores it transcription outputs (json files)
    out_prefix = bucket_prefix + "output/"
    
    self_heal = CLM["self_heal"]

    # result_prefix is an internal folder under which this framework stores its results such as runs.csv, leaderbaord.txt
    result_prefix = bucket_prefix + "result/"
    role_arn = ACCESS["role_arn"]
    
    orc = Orchestrator(bucket, keywords_prefix, data_prefix, out_prefix, bucket_prefix, result_prefix)

    logger.info("calling orchestrator")
    orc.run(self_heal=self_heal, role_arn=role_arn)
    logger.info("run completed")
        
