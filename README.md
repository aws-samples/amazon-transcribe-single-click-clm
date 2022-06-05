# Single-click CLM framework for Amazon Transcribe
A single-click framework for building a custom language model (CLM) with Amazon Transcribe is supplied with this repository. The architectural diagram of this framework is shown below.

![Archiecture](/images/architecture.png)

The single-click CLM framework helps you in the following manner:

1. It simplifies building a custom language model in Amazon Transcribe.
2. You can easily check if CLM makes a difference or not for your audio assets.
3. You don't need to supply any training data. If you have it, you can supply but is not mandatory.
4. It learns words missed by Amazon Transcribe.
5. It lists words fixed by the CLM.

You need to give it two mandatory inputs, one optional input, and then click a button – it is that simple!

There is a configuration file that you need to fill. You need to supply it with some audio files and their human transcription (which we refer as ground truth)

Optionally you can also provide a list of keywords that are specific for your domain.

Behind the scenes, this framework will do the following: it downloads Wikipedia data as training data if you supplied keywords, reads your input files, runs Amazon Transcribe, runs a CLM model if one already exists, normalizes the output, calculates word error rates (WERs), saves results such as missed words and other meta data. It also creates a model leaderboard.

If the self-heal option is turned on, the framework will first review all the words that were missed in the past runs. It will then go to Wikipedia, downloads training data specific to those missed words, and then trains a new CLM. This way, it is learning from its past mistakes and is self-healing.

It doesn’t end there. If you have new audio files in the future, you can add them to your inputs, and it will update past results with new results, and the model leaderboard. Let us say your new CLM model is not better than a past CLM model, then it will tell you so in the model leaderboard.

Steps to use this framework:

1. Modify the config.py file to point to your bucket, bucket-prefix (where the files will be), select whether to self-heal or not, and the ARN for your IAM role to train a new CLM.
2. Under your bucket prefix, create a folder named "input". Under "input", create sub-folders for each sample audio file that you have along with its human transcription (referred as ground-truth)

Sample config.py and "input" folder are shown below.

![Sample config file](/images/sample-config.png)

![Sample input folder](/images/sample-input.png)

Give any name to the sub-folders (folder-1, etc), except for a number (don't name sub-folder as "1" or similar).

Create a text file named "keywords.txt" and fill it with keywords from your domain. Separate each keyword in that file with a comma. A sample keywords.txt is supplied to you with this repository in the folder "sample-data". Place your keywords.txt file under a folder named "keywords" directly under your bucket-prefix. Although this file is optional, supplying these keywords can help you build a better custom model. This folder structure will look as follows in your S3 bucket: bucket-prefix/keywords/keywords.txt

IAM policies:

User access:
The IAM user that runs this framework needs to have the following policies:
- AmazonTranscribeFullAccess
- ComprehendFullAccess
- S3accesspolicy (look or a sample of this under the "policies" folder of this repo - fix it with your own bucket path)
- IAMPassrolepolicy (look for a sample of this under the "policies" folder of this repo - fix it with your own role arn)

Role access:
The role that is passed in the config file needs to have the following policies:
- AmazonTranscribeFullAccess
- Access to the S3 bucket where training data resides
- trustpolicy (look for a sample under the "policies" folder of this repo)

Once the above configurations are complete, you can run main.py as 'python main.py'

If you are running this framework from your laptop, it is recommended that you run it under a virtual environment. Install all dependencies from requirements.txt before running the program. Steps are shown below.

After cloning this code to your laptop, go to that directory

$ python3 -m venv my-venv

$ source my-venv/bin/activate

$ pip install -r requirements.txt

$ python main.py

Once completed, you can deactivate the virtual environment:

$ deactivate
