#!/usr/bin/python3
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
    width = ''
    height = ''
    file = ''
    try:
        opts, args = getopt.getopt(argv,"hf:i:o:x:y:",["file=", "idir=","odir=", "width=", "height="])
        if len(opts) != 5:
            print('264Tojpeg.py -f <file> -i <inputdir> -o <outputdir> -x <width> -y <height>')
            sys.exit()
    except getopt.GetoptError as e:
        print (e)
        print('264Tojpeg.py -f <file> -i <inputdir> -o <outputdir> -x <width> -y <height>')
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print('264Tojpeg.py -f <file> -i <inputdir> -o <outputdir> -x <width> -y <height>')
            sys.exit()
        elif opt in ("-i", "--idir"):
            input_dir = arg
        elif opt in ("-o", "--odir"):
            output_dir = arg
        elif opt in ("-x", "--width"):
            width = arg
        elif opt in ("-y", "--height"):
            height = arg
        elif opt in ("-f", "--file"):
            file = arg


    print('file: ', file)
    print('输入的目录为：', input_dir)
    print('输出的目录为：', output_dir)
    print('witdh:', width)
    print('height:', height)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect("10.12.11.222", username="mm", port=22, password="mm")
    ftp = ssh.open_sftp()
    ftp.put(input_dir+"/"+file , "/home/mm/denny/H264_To_JPEG/"+file)

    dir_command = "cd /home/mm/denny/H264_To_JPEG"
    env_command = "export LD_LIBRARY_PATH=/home/mm/denny/H264_To_JPEG/:$LD_LIBRARY_PATH"
    demo_command = "./demo "+file+" ./ " + width + " " + height
    tar_command = "tar -zcvf test.tar.gz *.jpg"
    clean_command = "rm -rf *.jpg test.tar.gz"+file

    command = dir_command+";"+env_command+";"+demo_command+";"+tar_command
    post_command = dir_command +";"+clean_command

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    print(ssh_stdout.read())
    print(ssh_stderr.read())

    ftp.get("/home/mm/denny/H264_To_JPEG/test.tar.gz",output_dir+"/test.tar.gz")

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


