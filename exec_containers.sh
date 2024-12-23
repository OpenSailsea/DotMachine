#!/bin/bash

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项] <命令>"
    echo "选项:"
    echo "  -a, --all         在所有容器中执行命令"
    echo "  -r, --range N-M   在指定ID范围的容器中执行命令 (例如: 1-10)"
    echo "  -h, --help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -a 'ls /root'              # 在所有容器中执行命令"
    echo "  $0 -r 1-5 'whoami'            # 在ID为1到5的容器中执行命令"
    echo "  $0 --range 10-20 'df -h'      # 在ID为10到20的容器中执行命令"
}

# 在指定容器中执行命令
exec_in_container() {
    local id=$1
    local cmd=$2
    local container_name="dotm-$id"
    
    # 检查容器是否存在并运行
    if sudo docker ps -q -f name=$container_name | grep -q .; then
        echo "正在容器 $container_name 中执行命令: $cmd"
        echo "----------------------------------------"
        # 使用bash -c来执行命令,并以root用户身份运行
        sudo docker exec -u root $container_name bash -c "$cmd"
        local exit_code=$?
        echo "----------------------------------------"
        if [ $exit_code -eq 0 ]; then
            echo "✓ 命令在容器 $container_name 中执行成功"
        else
            echo "✗ 命令在容器 $container_name 中执行失败 (退出码: $exit_code)"
        fi
        echo ""
    else
        echo "⚠ 容器 $container_name 不存在或未运行"
        echo ""
    fi
}

# 解析命令行参数
PARAMS=""
while (( "$#" )); do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -a|--all)
            ALL=true
            shift
            ;;
        -r|--range)
            if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
                RANGE=$2
                shift 2
            else
                echo "错误: --range 需要一个参数"
                exit 1
            fi
            ;;
        --) # 结束参数解析
            shift
            PARAMS="$PARAMS $*"
            break
            ;;
        -*|--*=) # 未知选项
            echo "错误: 未知选项 $1"
            exit 1
            ;;
        *) # 保留命令中的所有参数
            PARAMS="$PARAMS $1"
            shift
            ;;
    esac
done

# 恢复参数并设置命令
eval set -- "$PARAMS"
COMMAND="$*"

# 验证参数
if [ -z "$COMMAND" ]; then
    echo "错误: 必须指定要执行的命令"
    show_help
    exit 1
fi

if [ -z "$ALL" ] && [ -z "$RANGE" ]; then
    echo "错误: 必须指定 -a/--all 或 -r/--range 选项"
    show_help
    exit 1
fi

# 处理范围参数
if [ ! -z "$RANGE" ]; then
    if ! [[ $RANGE =~ ^[0-9]+-[0-9]+$ ]]; then
        echo "错误: 范围格式无效，应为 'N-M' (例如: 1-10)"
        exit 1
    fi
    START_ID=${RANGE%-*}
    END_ID=${RANGE#*-}
    if [ $START_ID -gt $END_ID ]; then
        echo "错误: 起始ID必须小于或等于结束ID"
        exit 1
    fi
fi

# 如果指定了 -a/--all，从配置文件获取所有容器ID
if [ "$ALL" = true ]; then
    if [ ! -f "containers.json" ]; then
        echo "错误: 找不到配置文件 containers.json"
        exit 1
    fi
    # 获取所有容器ID
    if ! IDS=$(jq -r '.containers | keys[]' containers.json 2>/dev/null); then
        echo "错误: 无法解析配置文件，请确保已安装jq"
        echo "Ubuntu/Debian: sudo apt-get install jq"
        echo "CentOS/RHEL: sudo yum install jq"
        exit 1
    fi
    
    if [ -z "$IDS" ]; then
        echo "没有找到任何容器"
        exit 0
    fi
    # 执行命令
    for id in $IDS; do
        exec_in_container $id "$COMMAND"
    done
else
    # 在指定范围内执行命令
    for id in $(seq $START_ID $END_ID); do
        exec_in_container $id "$COMMAND"
    done
fi

echo "命令执行完成!"
