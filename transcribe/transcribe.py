# all transcribe functions
import boto3, uuid, json, time

# reads Amazon Transcribe output (json file) from an S3 bucket location and returns transcription
def getTranscribe(outBucket, outKey):
    my_session = boto3.session.Session()
    my_region = my_session.region_name
    
    s3client = boto3.client(
        's3',
        region_name = my_region
    )
    #Create a file object using the bucket and object key. 
    fileobj = s3client.get_object(
        Bucket=outBucket,
        Key=outKey
        ) 
    # open the file object and read it into the variable filedata. 
    filedata = fileobj['Body'].read()
    # file data will be a binary stream.  We have to decode it 
    contents = filedata.decode('utf-8') 
    # Once decoded, you can treat the file as plain text if appropriate 
    return json.loads(contents)["results"]["transcripts"][0]['transcript']


class Transcribe:
    def __init__(self):
        self.clm_model_name = None
        
    # Trains a custom language model
    def __train_clm(self, training_data_s3, role_arn, uuid):
        client = boto3.client('transcribe')
        my_uuid = uuid #str(uuid.uuid4())
        model_name = 'clm-model-' + my_uuid
        self.clm_model_name = model_name
        response = client.create_language_model(
            LanguageCode='en-US',
            BaseModelName='WideBand',
            ModelName=model_name, # give a unique name to your model
            InputDataConfig={
                'S3Uri': training_data_s3, # location of training data
                #'TuningDataS3Uri': 's3://sample-bucket-1/tune', #optional tuning data
                'DataAccessRoleArn': role_arn #IAM execution role
            }
    )
        
    # Checks training status
    def __check_clm_status(self):
        client = boto3.client('transcribe')
        status = client.describe_language_model(
            ModelName=self.clm_model_name
        )
        return status["LanguageModel"]['ModelStatus']
    
    # Method to call Transcribe's custom language model (CLM), when a trained custom language model is already available
    def __clmTranscribe(self, mediaS3, outBucket, outKey, jobName, clmModelName, langCode='en-US'):
        # Start transcription
        client = boto3.client('transcribe')
        response = client.start_transcription_job(
            TranscriptionJobName = jobName,
            LanguageCode = langCode, #'en-US'
            ModelSettings={
                'LanguageModelName': clmModelName
            },
            Media = {
                'MediaFileUri': mediaS3
            },
            OutputBucketName = outBucket,
            OutputKey = outKey
    )
        
    # Method to call the standard Transcribe service
    def __standardTranscribe(self, mediaS3, outBucket, outKey, jobName, langCode='en-US'):
        client = boto3.client('transcribe')
        # Start transcription
        response = client.start_transcription_job(
            TranscriptionJobName = jobName,
            LanguageCode = langCode, #'en-US'
            Media = {
                'MediaFileUri': mediaS3
            },
            OutputBucketName = outBucket,
            OutputKey = outKey
    )
        
    # Given a media file (mp3, mp4), runs Amazon Transcribe and returns transcription text
    def get_standard_transcribe_text(self, mediaS3, outBucket, outPrefix, uuid):
        client = boto3.client('transcribe')
        # run standard transcription
        my_uuid = uuid
        jobName = "st-job-" + my_uuid
        if outPrefix[-1]!="/": outPrefix = outPrefix + "/"
        outKey = outPrefix + "st-" + my_uuid + ".json"
        self.__standardTranscribe(mediaS3, outBucket, outKey, jobName)
        
        # return standard transcription text
        status = client.get_transcription_job(TranscriptionJobName = jobName)['TranscriptionJob']['TranscriptionJobStatus']
        print(status)
        while status != "COMPLETED" and status != "FAILED":
            time.sleep(60)
            status = client.get_transcription_job(TranscriptionJobName = jobName)['TranscriptionJob']['TranscriptionJobStatus']
            print(status)
        return getTranscribe(outBucket, outKey)
    
    # Train a CLM Model
    def train_clm(self, training_data_s3, role_arn, uuid):
        self.__train_clm(training_data_s3, role_arn, uuid)
        status = self.__check_clm_status()
        while status != "COMPLETED" and status != "FAILED":
            time.sleep(90)
            status = self.__check_clm_status()
            print(status)
        clmModelName = self.clm_model_name
        return clmModelName
        
    # Given a media file (mp3, mp4), runs a custom language model (CLM) and returns transcription text
    # If clmModelName is None, it will first train a CLM model using the training_data_s3 location and then runs it
    def get_clm_transcribe_text(self, mediaS3, outBucket, outPrefix, uuid, clmModelName=None, training_data_s3=None, role_arn=None):
        client = boto3.client('transcribe')
        # build CLM model if needed
        if not clmModelName: # if clmModelName is None
            clmModelName = self.train_clm(training_data_s3, role_arn, uuid)
        # run CLM transcription
        my_uuid = uuid
        jobName = "clm-job-" + my_uuid
        if outPrefix[-1]!="/": outPrefix = outPrefix + "/"
        outKey = outPrefix + "clm-" + my_uuid + ".json"
        self.__clmTranscribe(mediaS3, outBucket, outKey, jobName, clmModelName)
        
        # return CLM transcroption text
        status = client.get_transcription_job(TranscriptionJobName = jobName)['TranscriptionJob']['TranscriptionJobStatus']
        print(status)
        while status != "COMPLETED" and status != "FAILED":
            time.sleep(60)
            status = client.get_transcription_job(TranscriptionJobName = jobName)['TranscriptionJob']['TranscriptionJobStatus']
            print(status)
        return getTranscribe(outBucket, outKey), clmModelName
    
    
if __name__ == "__main__":
    bucket = "my-bucket"
    outPrefix = "solutions/transcribe_clm/output/"
    mediaS3 = "s3://my-bucket/solutions/transcribe_clm/input/Biology_1.mp3"
    transcribe = Transcribe()
    stText = transcribe.get_standard_transcribe_text(mediaS3, bucket, outPrefix)
    clmText = transcribe.get_clm_transcribe_text(mediaS3, bucket, outPrefix, clmModelName="test-clm-model-1")
    
    print("stText=", stText)
    print("clmText=", clmText)
        