#!/usr/bin/python
# -*- coding: UTF-8 -*-
import paramiko
import os
import sys,getopt

def sftp_copy(conn,inpath,outpath):

    ftp = conn.open_sftp()
    ftp.put(inpath,outpath)
    ftp.close()
    return outpath

def main(argv):
    input_dir = ''
    output_dir = ''
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["idir=","odir="])
        if len(opts) != 2:
            print('264Tojpeg.py -i <inputdir> -o <outputdir>')
            sys.exit()
    except getopt.GetoptError as e:
        print (e)
        print('264Tojpeg.py -i <inputdir> -o <outputdir>')
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print('264Tojpeg.py -i <inputdir> -o <outputdir>')
            sys.exit()
        elif opt in ("-i", "--idir"):
            input_dir = arg
        elif opt in ("-o", "--odir"):
            output_dir = arg
    print('输入的目录为：', input_dir)
    print('输出的目录为：', output_dir)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect("10.12.11.222", username="mm", port=22, password="mm")
    ftp = ssh.open_sftp()
    ftp.put(input_dir+"/front_wide.h264","/home/mm/xulei/H264_To_JPEG/front_wide.h264")

    dir_command = "cd /home/mm/xulei/H264_To_JPEG"
    env_command = "export LD_LIBRARY_PATH=/home/mm/xulei/H264_To_JPEG/:$LD_LIBRARY_PATH"
    demo_command = "./demo front_wide.h264 ./ 2896 1876"
    tar_command = "tar -zcvf test.tar.gz *.jpg"
    clean_command = "rm -rf *.jpg test.tar.gz front_wide.h264"

    command = dir_command+";"+env_command+";"+demo_command+";"+tar_command
    post_command = dir_command +";"+clean_command

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    print(ssh_stdout.read())
    print(ssh_stderr.read())

    ftp.get("/home/mm/xulei/H264_To_JPEG/test.tar.gz",output_dir+"/test.tar.gz")

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(post_command)
    print(ssh_stdout.read())
    print(ssh_stderr.read())
    os.system('cd '+output_dir)
    os.system('cd '+output_dir+';tar -xvf test.tar.gz')
    os.system('rm -rf '+output_dir+'/test.tar.gz')

    ftp.close()

    ssh.close()

if __name__ == "__main__":
    main(sys.argv[1:])


