# Word Error Rate (WER) calculation using asr-evaluation
import subprocess
import uuid, os

# writes texts to a file
def write_to_file(fn, text):
    text_file = open(fn, "w")
    n = text_file.write(text)
    text_file.close()
    
# removes line breaks in text
def removeLineBreaks(text):
    return text.replace('\r', ' ').replace('\n', ' ')

# removes punctuations in text
def removePunctAndLB(text):
    text = text.replace('.', '').replace(',', '')
    return removeLineBreaks(text)

# returns text from a file
def readTextFromFile(fn):
    with open(fn) as f:
        text = f.read()
    f.close()
    return text
    
# Class to calculate word error rate (WER) using open source package asr-evaluation
class AsrEval:
    # Token used by asr-evaluation
    def get_missed_words(ref):
        TOKEN = "\x1b[31m"
        
    # calculate WER based on ground-truth and actual transcription text file names
    def get_WER_FN(self, gtFN, transcribeFN):
        gt_text = readTextFromFile(gtFN)
        transcribe_text = readTextFromFile(transcribeFN)
        
        return self.get_WER_REF(gt_text, transcribe_text)
    
    # calculate WER based on ground-truth and actual transcription texts arguments
    # returns WER and sentences along with errors
    # wer "-a" makes is case-insensitive
    # wer "-i" prints all individual sentences and their errors
    def get_WER_REF(self, gt_text, transcribe_text):
        gt_text = removePunctAndLB(gt_text)
        transcribe_text = removePunctAndLB(transcribe_text)
        gtFN = "gt.txt"
        write_to_file(gtFN, gt_text)
        
        transcribeFN = "tr.txt"
        write_to_file(transcribeFN, transcribe_text)
        
        result = subprocess.run(["wer", "-a", "-i", gtFN, transcribeFN], stdout=subprocess.PIPE)
        out = str(result.stdout)

        start = out.find("WER:")
        end = out.find("%",start)
        wer = out[start+4:end].strip()
        
        start = out.find("REF")
        end = out.find("HYP",start)
        ref = out[start+4:end].strip()
        
        os.remove(gtFN)
        os.remove(transcribeFN)
        return wer.strip(), ref
    
    # calculate WER based on ground-truth and actual transcription texts arguments
    # returns WER and sentences
    # wer "-a" makes is case-insensitive
    def get_WER(self, gt_text, transcribe_text):
        gt_text = removePunctAndLB(gt_text)
        transcribe_text = removePunctAndLB(transcribe_text)
        
        gtFN = "gt.txt"
        write_to_file(gtFN, gt_text)
        
        transcribeFN = "tr.txt"
        write_to_file(transcribeFN, transcribe_text)
        
        result = subprocess.run(["wer", "-a", gtFN, transcribeFN], stdout=subprocess.PIPE)
        out = str(result.stdout)

        start = out.find("WER")
        end = out.find("%",start)
        wer = out[start+4:end].strip()
        
        start = out.find("REF")
        end = out.find("HYP",start)
        ref = out[start+4:end].strip()
        
        os.remove(gtFN)
        os.remove(transcribeFN)
        return wer.strip(), ref
        
if __name__ == "__main__":
    asr = AsrEval()
    gt = "some ground truth input"
    hyp = "some hypothesis input"
    wer, ref = asr.get_WER(gt, hyp)
    print("wer=", wer)
    #print(ref)