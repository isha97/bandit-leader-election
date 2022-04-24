import glob, os
from collections import Counter
os.chdir("logs")


def print_message_freq(file):
    print("Printing for file : ", file)
    message_dict = Counter()
    with open(file) as f:
        lines = f.readlines()
        for line in lines:
            if len(line.split("     ")) > 1:
                line = line.split("     ")[1]
            else:
                continue
            if not line.startswith("receive"):
                continue
            words = line.split(" ")
            for word in words:
                if word.startswith("[Message]"):
                    message_dict[word[9:]] += 1
    for key in message_dict:
        print(key, "\t", message_dict[key])



for file in glob.glob("*.log"):
    print_message_freq(file)