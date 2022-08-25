#!/bin/bash

## Utils
##############################
declare -r PID=$$ # 获得当前进程
DATE_FORMAT=`date "+%Y-%m-%d %H:%M:%S"`
script_path=$(cd $(dirname "$0") && pwd)
function VarPrint()
{
    local var_name="$1"
    local var="$2"
    echo -e [line: `caller 0 |awk '{print $1}'` ] "\e[0;32m${var_name}\e[m:" $var
}
function INFO()
{
    echo -e "\e[0;32m[INFO]\e[m $@" >&2
}
function ERROR()
{
    echo -e "\e[0;41m[INFO]\e[m $@" >&2
    exit -1
}
VarPrint "script_path: " ${script_path}

## Funcion
################################
function print_help()
{
        echo -e "\e[1;34m ---------------------With Argument------------------\e[0m"
        echo -e "\e[1;34m Usage0: $0 -s source_dir -d destination_dir -f fps \e[0m"
        echo -e "\e[1;34m ---------------------No Argument------------------\e[0m"
        echo -e "\e[1;34m Usage1: $0 \e[0m"
        exit 1
}

function rename_jpg()
{
    if [[ ! -d "${SOURCE_DIR}" ]]; then
        ERROR "Input Source Dir is not exist,Please check"
    fi
    cd ${SOURCE_DIR}
    Count=1
    for line in $(ls *.jp)
    do
       # echo "find  ${line}"
        name0=$(printf "%04d" $Count)
        mv -f ${line}    $name0".jpg"
        (( Count = Count+1 ))
    done
        INFO "Rename jpg OK"
}
function jpg2mp4()
{
    if [[ ! -d "${DESTINATION_DIR}" ]]; then
        ERROR "Input Destination Dir is not exist,Please check"
    fi
    # 转换命令
    /opt/local/bin/ffmpeg -r ${FPS} -i ${SOURCE_DIR}/%4d.jpg ${DESTINATION_DIR}/output.mp4
}



## Main
#################################
# Read Args
GETOPT_ARGS=`getopt -o s:d:h::f: -- "$@"`
[ $? -ne 0 ] && print_help && exit 1
eval set -- "$GETOPT_ARGS"
while [ -n "$1" ]; do
	case "$1" in
		-s) SOURCE_DIR="$2"; shift 2;;
		-d) DESTINATION_DIR="$2"; shift 2;;
		-f) FPS="$2"; shift 2;;
		--) break;;
		-h) print_help; break;;
		*) print_help; break;;
	esac
done

[ -z "$SOURCE_DIR" ] && echo -e "\e[1;33m Source Dir is null,use script path!!!\e[0m!" && SOURCE_DIR=${script_path}
[ -z "$DESTINATION_DIR" ] && echo -e "\e[1;33m Destination Dir is null,use script path!!!\e[0m!" && DESTINATION_DIR=${script_path}
[ -z "$FPS" ] && FPS=5

VarPrint "Src: " ${SOURCE_DIR}
VarPrint "Dest: " ${DESTINATION_DIR}

# 必须先重命名jpg
rename_jpg
# 转换jpg2mp4
jpg2mp4
INFO "jpeg 2 mp4 Done"





