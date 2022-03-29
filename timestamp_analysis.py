#!/usr/bin/python3

import os
import argparse
import shutil
import matplotlib.pyplot as plt
import numpy as np

#files = ['Forward1.txt', 'Forward2.txt', 'Forward3.txt', 'Surround1.txt', 'Surround2.txt', 'Surround3.txt', 'Surround4.txt']
# files = ['right_fisheye_yuv420p.txt', 'left_fisheye_yuv420p.txt', 'rear_fisheye_yuv420p.txt', 'front_fisheye_yuv420p.txt', 'right_rear_yuv420p.txt', 'left_rear_yuv420p.txt', 'front_wide_yuv420p.txt', 'front_far_yuv420p.txt', 'right_front_yuv420p.txt', 'left_front_yuv420p.txt', 'rear_mid_yuv420p.txt']
# files = ['right_fisheye_nvmedia.txt', 'left_fisheye_nvmedia.txt', 'rear_fisheye_nvmedia.txt', 'front_fisheye_nvmedia.txt', 'right_rear_nvmedia.txt', 'left_rear_nvmedia.txt', 'front_wide_nvmedia.txt', 'front_far_nvmedia.txt', 'right_front_nvmedia.txt', 'left_front_nvmedia.txt', 'rear_mid_nvmedia.txt']
# files = ['right_fisheye_h264.txt', 'left_fisheye_h264.txt', 'rear_fisheye_h264.txt', 'front_fisheye_h264.txt', 'right_rear_h264.txt', 'left_rear_h264.txt', 'front_wide_h264.txt', 'front_far_h264.txt', 'right_front_h264.txt', 'left_front_h264.txt', 'rear_mid_h264.txt']
# files = ['right_fisheye_jpeg.txt', 'left_fisheye_jpeg.txt', 'rear_fisheye_jpeg.txt', 'front_fisheye_jpeg.txt', 'right_rear_jpeg.txt', 'left_rear_jpeg.txt', 'front_wide_jpeg.txt', 'front_far_jpeg.txt', 'right_front_jpeg.txt', 'left_front_jpeg.txt', 'rear_mid_jpeg.txt']

### 6 channel cameras
files = ['right_fisheye_yuv420p.txt', 'left_fisheye_yuv420p.txt', 'rear_fisheye_yuv420p.txt', 'front_fisheye_yuv420p.txt', 'front_wide_yuv420p.txt', 'front_far_yuv420p.txt']

# files = ['right_fisheye_jpeg.txt', 'left_fisheye_jpeg.txt', 'rear_fisheye_jpeg.txt', 'front_fisheye_jpeg.txt', 'front_wide_jpeg.txt', 'front_far_jpeg.txt', 'right_front_jpeg.txt']

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
            #  print("i=%d j=%d timestamp[i][j]=%d" %(i, j, int(timestamp[i][j])))
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
    camera_show = args["c"]
    base = int(args["b"])
    interval = int(args["i"])
    frameNum = [[] for i in range(len(files))]
    timestamp = [[] for i in range(len(files))]
    recv_ts = [[] for i in range(len(files))]
    info = [4]
    min_linecount = 0
    linecount = 0
    for i in range(len(files)):
        f = open(filepath + '/' + files[i], 'r')
        linecount = 0
        line = f.readline()
        while line:
            line = line.strip()
            info = line.split('.')
            frameNum[i].append(info[0])
            timestamp[i].append(info[1])
            recv_ts[i].append(info[2])
            line = f.readline()
            linecount = linecount + 1
        f.close()
        print("%s line count is %d" % (files[i], linecount))
        if min_linecount == 0:
            min_linecount = linecount
        if linecount < min_linecount:
            min_linecount = linecount
        
    print("min line count is %d" % min_linecount)

    if interval == 0:
        frame_sync_test(timestamp, min_linecount, camera_show, base)
    elif interval == 1:
        frame_interval_test(frameNum, timestamp, min_linecount, camera_show)
    elif interval == 2:
        frame_time_consuming_test(timestamp, recv_ts, min_linecount, camera_show)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", default=None, required=True, help="input images path")
    parser.add_argument("-c", default=None, required=True, help="input camera id that will be show")
    parser.add_argument("-b", default=0, required=True, help="the base timestamp of camera id")
    parser.add_argument("-i", default=0, required=True, help="drow the interval of two frames")
    
    args = parser.parse_args()

    analyse_filelist(vars(args))
    exit(0)
