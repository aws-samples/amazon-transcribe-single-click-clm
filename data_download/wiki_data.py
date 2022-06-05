import nltk
nltk.download('punkt')
nltk.download('stopwords')

from nltk import tokenize
import re
import urllib.request
from bs4 import BeautifulSoup
import urllib.request
from bs4 import BeautifulSoup
import boto3

# Gets last modified date for a S3 object
def getLastModified(bucket, key):
    s3_client = boto3.client(service_name='s3')
    result = s3_client.get_object(Bucket=bucket, Key=key) 
    return result['LastModified']

# Gets last modified date for a S3 folder
def getLastModifiedPrefix(bucket, prefix):
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket)
    for object_summary in my_bucket.objects.filter(Prefix=prefix):
        return getLastModified(bucket, object_summary.key)
    return None # if no objects in that prefix

# Writes text to S3 as a file
def writeTextToS3(bucket, key, content):
    s3_client = boto3.client('s3')
    s3_client.put_object(Body=content, Bucket=bucket, Key=key)
    
# Returns all files under an S3 prefix
def listS3Files(bucket, prefix):
    s3 = boto3.resource('s3')
    my_bucket = s3.Bucket(bucket)
    files = []
    for object_summary in my_bucket.objects.filter(Prefix=prefix):
        if object_summary.key[-1] != "/": # don't append parent directory name
            files.append(object_summary.key)
    return files

# Reads a file line by line from S3
def read_keywords_from_S3_file(bucket, key):
    keywords = []
    # connect to S3 using boto3 client
    s3_client = boto3.client(service_name='s3')
    # get S3 object
    result = s3_client.get_object(Bucket=bucket, Key=key) 
    #Read a text file line by line using splitlines object
    for line in result["Body"].read().splitlines():
        each_line = line.decode('utf-8').strip()
        for word in each_line.split(","):
            #print(word)
            if len(word.strip())>0:
                keywords.append(word.strip())
    return keywords

# Helper function to get html text from wikipedia
def extract_html(keyword):
    try:
        fp = urllib.request.urlopen("https://en.wikipedia.org/wiki/"+keyword)
        html = fp.read().decode("utf8")
        fp.close()
        return html
    except:
        print("Page for "+keyword+" does not exist")
        return None

# Helper function to extract data from html text
def get_data(html):
    extracted_data = []
    soup = BeautifulSoup(html, 'html.parser')
    for data in soup.find_all('p'):
        res = tokenize.sent_tokenize(data.text)
        for txt in res:
            txt2 = re.sub("[\(\[].*?[\)\]]", "", txt)
            txt2 = txt2.strip()
            if len(txt2)>0:
                extracted_data.append(txt2)
    return extracted_data

# check if new keywords are added to the keywords file or if keywords were never downloaded
def new_keywords(bucket, keywords_file, prefix):
    kf_ts = getLastModified(bucket, keywords_file)
    prefix_ts = getLastModifiedPrefix(bucket, prefix)
    if prefix_ts == None: return True
    if kf_ts > prefix_ts:
        val = True
    else:
        val = False
    return val

# Class to handle wikipedia data downloads
class WikiData:
    # Download data from wikipedia to local text files
    def download_data(self, bucket, data_prefix, keywords_prefix):
        k_files = listS3Files(bucket, keywords_prefix)

        for keywords_file in k_files:
            if not new_keywords(bucket, keywords_file, data_prefix): continue # no need to download new training data

            self.keywords_list = read_keywords_from_S3_file(bucket, keywords_file)
            count = 0
            for keyword in self.keywords_list:
              keyword = keyword.replace(" ","_")
              html = extract_html(keyword)
              if html:
                  count += 1
                  data = "\n".join(get_data(html))
                  writeTextToS3(bucket=bucket, key=data_prefix+keyword+".txt", content=data)

            print("Was able to download text for "+ str(count) + " out of "+str(len(self.keywords_list))+" keywords")
        
if __name__ == "__main__":
    bucket = "my-bucket"
    wd = WikiData()
    wd.download_data(bucket, "solutions/transcribe_clm/training_data/", "solutions/transcribe_clm/keywords/")