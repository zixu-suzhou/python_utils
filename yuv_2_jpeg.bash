#! /bin/bash

ROOT_PATH=`pwd`
cd $ROOT_PATH/

function HAHA
{
        echo "—————————————————————————————— HAHA Argument ——————————————————————————————"
        echo "|  ./YUV_2_JPEG.sh <YUV_Path> <JPEG_Path>                                     |"
        echo "———————————————————————————————————————————————————————————————————————————"
        exit -1
}


# 输入输出文件夹操作
Input_YUV_Path=$1
Output_JPEG_Path=$2
if [ ! -n "$1" ] ;then
	Input_YUV_Path=./
fi
if [ ! -n "$2" ] ;then
	Output_JPEG_Path=./
fi

echo "INFO : Input  YUV  Path = "${Input_YUV_Path}
echo "INFO : Output JPEG Path = "${Output_JPEG_Path}


# 判断文件夹是否存在 -d
if [[ ! -d "${Input_YUV_Path}" ]]; then
	echo "Error: Input  YUV  Path not exist, please check !"
else
	Total_YUV_File_In_Input_Path=`ls ${Input_YUV_Path} | grep .yuv | wc -l`
	echo "INFO : Total find "${Total_YUV_File_In_Input_Path}" YUV files in "${Input_YUV_Path}
fi
if [[ ! -d "${Output_JPEG_Path}" ]]; then
    echo "WARN : Output YUV  Path not exist, MKDIR !"
	mkdir ${Output_JPEG_Path}
fi


# 自动识别分辨率,从而获取 YUV 的格式


# 将 YUV 编码为 JPEG
function Do_JPEG_Encode
{
	for YUV_File_Name in `ls $Input_YUV_Path | grep .yuv`
	do
		ls -l ${one_yuv_file}
		YUV_File_Size=`wc -c ${Input_YUV_Path}/${YUV_File_Name} | awk '{print $1}'`

		# 根据文件大小，判断 YUV 文件的分辨率和格式
		YUV_File_Fromat="yuv420p"
		YUV_File_Resolv="2896x1876"
		if [[ "${YUV_File_Size}" == "8149344" ]]; then
			YUV_File_Fromat="yuv420p"
			YUV_File_Resolv="2896x1876"
		elif [[ "${YUV_File_Size}" == "3131264" ]]; then
			YUV_File_Fromat="nv12"
			YUV_File_Resolv="1936x1216"
		elif [[ "${YUV_File_Size}" == "1843200" ]]; then
			YUV_File_Fromat="yuv420p"
			YUV_File_Resolv="1280x960"
		elif [[ "${YUV_File_Size}" == "10865792" ]]; then
			YUV_File_Fromat="yuyv422"
			YUV_File_Resolv="2896x1876"
		elif [[ "${YUV_File_Size}" == "4708352" ]]; then
			YUV_File_Fromat="yuyv422"
			YUV_File_Resolv="1936x1216"
		elif [[ "${YUV_File_Size}" == "2457600" ]]; then
			YUV_File_Fromat="yuyv422"
			YUV_File_Resolv="1280x960"
		fi

		echo ${YUV_File_Name}

		# 删除字符串左边第一个.右边的所有内容，为了获取文件的时间戳，用来给 JPEG 文件命名
		YUV_File_TimeStamp=${YUV_File_Name%.*}
		echo ${YUV_File_TimeStamp}

		# 最核心的 ffmpeg 命令
		# ffmpeg -pix_fmt yuyv422 -s 1280x960 -i 72030487.yuv 72030487.jpeg -y
		/opt/local/bin/ffmpeg -pix_fmt ${YUV_File_Fromat} -s ${YUV_File_Resolv} -i ${Input_YUV_Path}/${YUV_File_Name}  ${Output_JPEG_Path}/${YUV_File_TimeStamp}.jpeg -y
	done
}

Do_JPEG_Encode
