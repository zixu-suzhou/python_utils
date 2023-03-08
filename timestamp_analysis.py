#!/usr/bin/python3

import os
import argparse
import shutil
import matplotlib.pyplot as plt
import numpy as np
import glob

def analyse_filelist(args):
    filepath = args["p"]

    for file in glob.glob(filepath + '/camera_service.log*'):
        print("check TS in file %s" % file);
        f = open(file, 'r')
        line = f.readline()
        linecount = 0
        raw_ts = []
        raw_seq = []
        str_seq = "seq:"
        str_start = "raw_ts:"
        str_end = "ms"
        while line:
            line = f.readline()
            index_seq = line.find(str_seq)
            index_start = line.find(str_start)
            index_end = line.find(str_end)
            if index_seq != -1:
                ts = line[index_start + 7:index_end]
                seq = line[index_seq +4:index_start - 1]
                if linecount > 2 and int(ts) < int(raw_ts[-1]) + 90:
                    print("raw ts error on seq %s - %s, with TS = %s - %s us" %(raw_seq[-1],seq,raw_ts[-1], ts))
                raw_ts.append(ts);
                raw_seq.append(seq);
                linecount = linecount + 1
        f.close()

        x = np.array(raw_seq, dtype = np.int64)
        y = np.array(raw_ts, dtype = int)
        plt.plot(x, y, label="imgbag raw ts")
        plt.xlabel("seq")
        plt.ylabel("ms")
        plt.legend()
        plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", default=None, required=True, help="input log path")

    args = parser.parse_args()

    analyse_filelist(vars(args))
    exit(0)
