# orchestrates the workflow

from data_download.wiki_data import WikiData
from transcribe.transcribe import Transcribe
from data_preparation.normalize_text import NormalizeText
from wer.asr import AsrEval
import pandas as pd
import io, operator
from io import StringIO

import boto3, uuid, logging, sys, re

logger = logging.getLogger()

# Parses keywords from missedwords of Transcribe and CLM
# Uses Amazon Comprehend
def parseKeywords(text):
    nouns = set()
    comprehend = boto3.client(service_name='comprehend', region_name=boto3.Session().region_name)
    syntax = comprehend.detect_syntax(Text=text, LanguageCode='en')
    for synt in syntax['SyntaxTokens']:
        pos = synt['PartOfSpeech']['Tag']
        if (pos == 'NOUN') | (pos == 'PROPN'):
            nouns.add(synt['Text'])
    return ", ".join(nouns)

# Returns text from a S3 file
def readS3TextFile(bucket, key):
    # connect to S3 using boto3 client
    s3_client = boto3.client(service_name='s3')
    try:
        # get S3 object
        result = s3_client.get_object(Bucket=bucket, Key=key) 
        text = result["Body"].read().decode('utf-8')
        return text
    except:
        return None # if key doesn't exist or other such exception occurs

# Saves text as a file in S3
def saveTextAsFileinS3(text, bucket, filename):
    s3 = boto3.resource('s3')
    object = s3.Object(bucket, filename)
    result = object.put(Body=text)
    
# Returns a list of all files under an S3 prefix
def listS3Files(bucket, prefix):
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket)
    files = []
    for object_summary in my_bucket.objects.filter(Prefix=prefix):
        files.append(object_summary.key)
    return files

# Updates the learned_keywords file
def update_missed_words(bucket, key, new_words):
    existing = readS3TextFile(bucket, key)
    if existing is not None:
        existing = [x.strip().capitalize() for x in existing.split(',')]
    else:
        existing = []
    new_ones = [x.strip().capitalize() for x in new_words.split(',')]
    existing.extend(new_ones)
    result = ', '. join(set(existing))
    saveTextAsFileinS3(result, bucket, key)

from nltk.corpus import stopwords
    
# Cleans text
def clean(text):
    text = text.strip()
    if "*" in text: return None
    if text.endswith("."): return None
    if text.endswith(","): return None
    if len(text)<3: return None
    return text.lower()
    
# Takes a reference object (from asr-evaluation) as input and returns a list of missed words
BTOKEN, ETOKEN = "\\x1b[31m", "\\x1b[0m"
def find_missed_words(ref):
    decoded_string = ref #ref.decode('utf-8')
    count = 0
    start = 0
    words = set()
    while True:
        count += 1
        begin = decoded_string.find(BTOKEN, start)
        if begin==-1: break
        end = decoded_string.find(ETOKEN, begin)
        word = decoded_string[begin+len(BTOKEN): end]
        cleaned = clean(word)
        if cleaned: words.add(cleaned.strip())
        start = end
        if start==-1: break
        if count>100: break
    filtered_words = [word for word in words if word not in stopwords.words('english')]
    #filtered_words = ", ".join(filtered_words)
    return filtered_words

# removes non-alphanumeric characters
def replaceNonAlpha(wordSet):
    newSet = set()
    for word in wordSet:
        s = re.sub('[^0-9a-zA-Z]+', '', word)
        newSet.add(s)
    return newSet

# Class that orchestrates downloading of training data from wikipedia, 
# runs standard transcription and CLM transcription on all input files,
# normalizes the transcription output, calculates WERs and stores the result in S3
class Orchestrator:
    def __init__(self, bucket, keywords_prefix, data_prefix, out_prefix, bucket_prefix, result_prefix):
        self.bucket = bucket
        self.keywords_prefix = keywords_prefix
        self.data_prefix = data_prefix
        self.out_prefix = out_prefix
        self.bucket_prefix = bucket_prefix
        self.result_prefix = result_prefix
        self.RUNS_FILE = "runs.csv"
        self.RUNS_DF = self.readRuns(bucket)
        
    # saves model leadership to S3
    def saveLeaderboard(self):
        df = self.RUNS_DF
        df['wer'] = df.wer.astype(float)
        df = df[df["wer"]>=0.0]
        g = df.groupby('model')
        result = {}
        output = "model-name: WER\n\n"
        for name, row in g:
            result[name] = row["wer"].mean()
        for key in dict(sorted(result.items(), key=operator.itemgetter(1))):
            if key == "ST":
                output += "Standard Transcribe (ST)" + ": "
            else:
                output += key + ": "
            output += str(result[key]) + "\n\n"
        saveTextAsFileinS3(output, self.bucket, self.result_prefix+"leaderboard.txt")
        
    # method to return CLM model names from past runs
    def getCLMNames(self):
        dftemp = self.RUNS_DF[self.RUNS_DF["model"] != "ST"]
        return dftemp["model"].unique()
    
    def get_ST_words(self, folder_name):
        dftemp = self.RUNS_DF[((self.RUNS_DF["model"]=="ST") & (self.RUNS_DF["folder"]==folder_name))]
        return list(dftemp["missed_words"])
        
    # method to read runs.csv file if it exists
    def readRuns(self, bucket):
        csvString = readS3TextFile(bucket, self.result_prefix + self.RUNS_FILE)
        if csvString != None:
            csvStringIO = StringIO(csvString)
            df = pd.read_csv(csvStringIO, sep=",")
            df['folder'] = df.folder.astype(str) # to take care of numerical folder namnes
        else:
            df = pd.DataFrame(columns=["model", "folder", "wer", "missed_words", "fixed_words"]) 
        return df
    
    # method to check if a given model (ST or CLM) was run against an input folder
    def ranBefore(self, model_name, input_folder):
        dftemp = self.RUNS_DF[((self.RUNS_DF["model"]==model_name) & (self.RUNS_DF["folder"]==input_folder))]
        if len(dftemp)==0: return False
        return True
        
    # method that runs all required steps in this transcription workflow
    def run(self, self_heal, role_arn=None):
        master_uuid = str(uuid.uuid4()) # unique id to connect related transcription runs
        transcribe = Transcribe()
        
        if self_heal:
            # read keywords file and download wiki files
            wd = WikiData()
            wd.download_data(self.bucket, self.data_prefix, self.keywords_prefix)
            logger.info("downloaded wikipedia data")
            
            # train a new CLM
            logger.info("start of new CLM model training")
            training_data_uri = "s3://" + self.bucket + "/" + self.data_prefix
            clmModelName = transcribe.train_clm(training_data_uri, role_arn, master_uuid)
            self.RUNS_DF.loc[len(self.RUNS_DF.index)] = [clmModelName, None, None, None, None]
            logger.info("new CLM model training completed")
            
        # makes a dictionary of input ground truth and audio files
        inputs = {}
        input_files = listS3Files(self.bucket, self.bucket_prefix+"input/")
        for myfile in input_files:
            if myfile[-1] != "/": # not a directory
                directory = myfile.split("/")[-2]
                #print(myfile, directory)
                if directory not in inputs: inputs[directory] = []
                inputs[directory].append(myfile)
        logger.info("read inputs ..")
        
        missed_words = set()
        clm_modelnames = self.getCLMNames()
        for key in inputs.keys():
            if inputs[key][0].endswith(".txt"):
                s3media = inputs[key][1]
                gt_file = inputs[key][0]
            else: 
                s3media = inputs[key][0]
                gt_file = inputs[key][1]
            s3media = "s3://" + self.bucket + "/" + s3media
            
            # load and normalize ground truth
            gtText = readS3TextFile(self.bucket, gt_file)
            normalize = NormalizeText()
            n_gtText = normalize.normalize(gtText)
                
            # run standard transription if it is not run before on this folder
            if not self.ranBefore("ST", str(key)):
                my_uuid = master_uuid + "-ST-" + str(key)
                # run standard transcription
                stText = transcribe.get_standard_transcribe_text(s3media, self.bucket, self.out_prefix, my_uuid)
        
                # normalize transcriptions
                normalize = NormalizeText()
                n_stText = normalize.normalize(stText)
        
                # calculate WERs
                wer_st, ref = AsrEval().get_WER_REF(n_gtText, n_stText)
                stwords = find_missed_words(ref)
                missed_words.update(stwords)
                logger.info("wer_st = " + wer_st)
            
                #self.RUNS_DF.loc[len(self.RUNS_DF.index)] = ['ST', str(key), wer_st, parseKeywords(str(stwords)), ""]
                stwords_str = ", ".join(stwords)
                self.RUNS_DF.loc[len(self.RUNS_DF.index)] = ['ST', str(key), wer_st, stwords_str, ""]
            
                logger.info("Standard Transcribe missed words: ")
                logger.info(stwords)
                #logger.info("\n")
                
            for clm_name in clm_modelnames:
                my_uuid = master_uuid + "-" + clm_name + "-" + str(key)
                if not self.ranBefore(clm_name, str(key)):
                    #training_data_uri = "s3://" + self.bucket + "/" + self.data_prefix
                    clmText, clmModelName = transcribe.get_clm_transcribe_text(s3media, self.bucket, self.out_prefix, my_uuid, \
                                    clmModelName=clm_name, training_data_s3=None, role_arn=role_arn)
                    normalize = NormalizeText()
                    n_clmText = normalize.normalize(clmText)
                    wer_clm, ref = AsrEval().get_WER_REF(n_gtText, n_clmText)
                    clmwords = find_missed_words(ref)
                    missed_words.update(clmwords)
                    logger.info("wer_clm = " + wer_clm)
                    logger.info("CLM missed words: ")
                    logger.info(clmwords)
            
                    fixedwords = []
                    stwords = self.get_ST_words(key)
                    for word in stwords:
                        if word not in clmwords: fixedwords.append(word)
                    fixedwords = ", ".join(fixedwords)
                    logger.info("Words fixed by CLM:")
                    logger.info(fixedwords)
                    clmwords_str = ", ".join(clmwords)
                    self.RUNS_DF.loc[len(self.RUNS_DF.index)] = [clm_name, str(key), wer_clm, clmwords_str, fixedwords]
                    
        s = io.StringIO()
        self.RUNS_DF.to_csv(s, index=False)
        save_csv = s.getvalue()
        saveTextAsFileinS3(save_csv, self.bucket, self.result_prefix + self.RUNS_FILE)
        if len(missed_words)>0:
            save_missedwords = str(parseKeywords(', '.join(missed_words)))
            update_missed_words(self.bucket, self.keywords_prefix + "learned_keywords.txt", save_missedwords)
            
        self.saveLeaderboard()