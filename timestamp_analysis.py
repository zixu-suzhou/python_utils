#!/usr/bin/python3

import os
import argparse
import shutil
import matplotlib.pyplot as plt
import numpy as np

### 8 channel cameras
files = ['right_fisheye_yuv420p.txt', 'left_fisheye_yuv420p.txt', 'rear_fisheye_yuv420p.txt', 'front_fisheye_yuv420p.txt', 'front_wide_yuv420p.txt', 'front_far_yuv420p.txt', 'left_rear_yuv420p.txt', 'right_rear_yuv420p.txt']


def get_FileSize(filePath):

    fsize = os.path.getsize(filePath)
    fsize = fsize/float(1024)

    return round(fsize, 2)

def make_issue_dir(path):
    pathlist = [2]
    pathlist = path.split('/')
    issue_dir_path = pathlist[0] + '/' + pathlist[1] + 'issue'
    os.makedirs(issue_dir_path + '/size')
    os.makedirs(issue_dir_path + '/timestamp')
    return issue_dir_path

def frame_interval_test(frameNum, timestamp, min_linecount, camera_show):
    diffvalue = [[] for i in range(len(files))]
    numArray = [[] for i in range(len(files))]
    for i in range(len(files)):
        for j in range(min_linecount-1):
            value = int(timestamp[i][j+1]) - int(timestamp[i][j])
            diffvalue[i].append(value)

    #x = np.arange(0, min_linecount, 1)
    #x = np.array(timestamp[0][1:min_linecount], dtype = int)
    #x = np.array(frameNum[1], dtype = int)
    #y = np.array(diffvalue[1], dtype = int)
    #print("x len is %d, y len is %d" % (len(x),len(y)))
    if camera_show == "x":
        for i in range(len(files)):
            info = files[i].split('.')
            camera_name = info[0]
            x = np.array(timestamp[0][1:min_linecount], dtype = int)
            y = np.array(diffvalue[i], dtype = int)
            plt.plot(x, y, label=camera_name)
    else:
        i = int(camera_show)
        info = files[i].split('.')
        camera_name = info[0]
        x = np.array(frameNum[i][1:min_linecount], dtype = int)
        y = np.array(diffvalue[i], dtype = int)
        plt.plot(x, y, label=camera_name)

    plt.xlabel("frame num")
    plt.ylabel("us")
    plt.legend()
    plt.show()

def find_first_timestamp(timestamp, min_linecount):
    tmplist = []
    start_seq = [0 for x in range(len(files))]
    for i in range(len(files)):
        tmplist.append(int(timestamp[i][100]))

    print(tmplist)
    max_ts = max(tmplist)
    print("max_ts=%d" % max_ts)
    for i in range(len(files)):
         for j in range(min_linecount):
             #print("i=%d j=%d timestamp[i][j]=%d" %(i, j, int(timestamp[i][j])))
             value = max_ts - int(timestamp[i][j])
             if (value >= 0 and value < 5000) or (value < 0 and value > -5000):
                start_seq[i] = j
                break;

    return start_seq

def frame_sync_test(timestamp, min_linecount, camera_show, base):
    start_seq = find_first_timestamp(timestamp, min_linecount)
    print(start_seq)
    diffvalue = [[] for i in range(len(files))]
    for i in range(len(files)):
         for j in range(start_seq[i], min_linecount):
             value = int(timestamp[base][start_seq[base]+(j-start_seq[i])]) - int(timestamp[i][j])
             diffvalue[i].append(value)

    if camera_show == "x":
        for i in range(len(files)):
            info = files[i].split('.')
            camera_name = info[0]
            x = np.array(timestamp[i][start_seq[i]:min_linecount], dtype = int)
            y = np.array(diffvalue[i], dtype = int)
            plt.plot(x, y, label=camera_name)
    else:
        i = int(camera_show)
        info = files[i].split('.')
        camera_name = info[0]
        x = np.array(timestamp[i][start_seq[i]:min_linecount], dtype = int)
        y = np.array(diffvalue[i], dtype = int)
        plt.plot(x, y, label=camera_name)

    plt.xlabel("frame num")
    plt.ylabel("us")
    plt.legend()
    plt.show()

def frame_time_consuming_test(timestamp, recv_ts, min_linecount, camera_show):
    diffvalue = [[] for i in range(len(files))]
    for i in range(len(files)):
        for j in range(min_linecount):
            value = int(recv_ts[i][j]) - int(timestamp[i][j])
            diffvalue[i].append(value)

    #x = np.arange(0, min_linecount, 1)
    x = np.array(timestamp[0][0:min_linecount], dtype = int)
    y = np.array(diffvalue[1], dtype = int)
    print("x len is %d, y len is %d" % (len(x),len(y)))
    if camera_show == "x":
        for i in range(len(files)):
            info = files[i].split('.')
            camera_name = info[0]
            y = np.array(diffvalue[i], dtype = int)
            plt.plot(x, y, label=camera_name)
    else:
        i = int(camera_show)
        info = files[i].split('.')
        camera_name = info[0]
        y = np.array(diffvalue[i], dtype = int)
        plt.plot(x, y, label=camera_name)

    plt.xlabel("frame num")
    plt.ylabel("us")
    plt.legend()
    plt.show()

def analyse_filelist(args):
    filepath = args["p"]

    f = open(filepath + '/camera_service.log', 'r')
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

    print("line count is %d" % linecount)
    #x = np.array(raw_seq, dtype = int)
    #y = np.array(raw_ts, dtype = int)
    #plt.plot(x, y, label="imgbag raw ts")
    #plt.xlabel("seq")
    #plt.ylabel("us")
    #plt.legend()
    #plt.show()




if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", default=None, required=True, help="input log path")

    args = parser.parse_args()

    analyse_filelist(vars(args))
    exit(0)
