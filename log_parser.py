import glob, os
from collections import Counter
os.chdir("logs")


def print_message_freq(file):
    print("Printing for file : ", file)
    message_dict_send = Counter()
    message_dict_recv = Counter()
    with open(file) as f:
        lines = f.readlines()
        for line in lines:
            if len(line.split("()")) > 1:
                line = line.split("()")[1]
            else:
                continue

            if "[RECV]" in line:
                words = line.split(" ")
                for word in words:
                    if word.startswith("[Message]"):
                        message_dict_recv[word[9:]] += 1

            elif "[SEND]" in line:
                print(line)
                words = line.split(" ")
                for word in words:
                    if word.startswith("[Message]"):
                        message_dict_send[word[9:]] += 1


    print("###### SEND STATS #######")
    for key in message_dict_send:
        print(key, "\t", message_dict_send[key])

    print("###### RECV STATS #######")
    for key in message_dict_recv:
        print(key, "\t", message_dict_recv[key])
    print("\n\n")

for file in glob.glob("*.log"):
    print_message_freq(file)