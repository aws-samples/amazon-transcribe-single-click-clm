# Text clean up

import re

# Helper function to remove paranthesis and content with it
def remove_paranthesis(inputStr):
    #return re.sub(r"\([^()]*\)", "", inputStr) #only remove ()
    return re.sub("[\(\[].*?[\)\]]", "", inputStr) #remove () and []

# Helper function to remove extra spaces in text
def remove_extra_spaces(inputStr):
    # remove additional space from string 
    inputStr = inputStr.strip()
    return re.sub(' +', ' ', inputStr)

# Helper function to remove ums, uhs, others, as well as punctuations
def remove_umuh_comma_dot(inputStr):
    wordList = ["Um", " um", "Uh", "uh", "Umm", "umm", "Mmm", "mmm", "Ah", "ah", ",", ".", ";", '"', ":"]
    for word in wordList:
        inputStr = inputStr.replace(word, '')
    return remove_extra_spaces(inputStr)

# Helper function to remove hyphen and longer dash
# example cow-calf changed to cow calf
def expand_dash(inputStr):
    inputStr = inputStr.replace("-", ' ')
    inputStr = inputStr.replace("—", ' ')
    return inputStr

# Helper function to normalize text before calculating WER
def normalize_text(inputStr):
    out = remove_paranthesis(inputStr)
    out = remove_umuh_comma_dot(out)
    out = expand_dash(out)
    return remove_extra_spaces(out)

# Class to cleanup text
class NormalizeText():
    def normalize(self, content):
        return normalize_text(content)

if __name__ == "__main__":
    nt = NormalizeText()
    text = nt.normalize("Hello testing uh the text() input")
    print(text)