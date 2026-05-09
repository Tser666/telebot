#!/bin/bash
# ============================================
# Oracle Cloud + Cloudflare WARP 一键安装脚本
# 适用：Ubuntu 20.04/22.04/24.04 (ARM64 或 x86_64)
# 功能：自动安装 Docker + WARP，配置 SOCKS5 代理
# 用法：bash <(curl -fsSL https://raw.githubusercontent.com/xxx/install.sh)
#       或：sudo bash install_warp_oracle.sh
# ============================================

set -e  # 遇到错误立即退出
clear

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否为 root 或有权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "当前不是 root 用户，将使用 sudo"
        if ! sudo -n true 2>/dev/null; then
            log_error "需要 sudo 权限，请运行：sudo bash $0"
            exit 1
        fi
    fi
}

# 检测系统架构
detect_arch() {
    local arch=$(uname -m)
    if [[ "$arch" == "aarch64" || "$arch" == "arm64" ]]; then
        echo "arm64"
    elif [[ "$arch" == "x86_64" || "$arch" == "amd64" ]]; then
        echo "amd64"
    else
        log_error "不支持的架构: $arch"
        exit 1
    fi
}

# 检测系统版本
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        echo "$ID $VERSION_ID"
    else
        log_error "无法检测系统版本"
        exit 1
    fi
}

# 安装基础依赖
install_deps() {
    log_info "安装基础依赖..."
    sudo apt update -y
    sudo apt install -y curl wget vim net-tools ca-certificates gnupg lsb-release
    log_success "基础依赖安装完成"
}

# 安装 Docker
install_docker() {
    if command -v docker &> /dev/null; then
        log_info "Docker 已安装，跳过"
        return
    fi
    
    log_info "安装 Docker..."
    sudo apt update -y
    sudo apt install -y docker.io
    
    # 启动 Docker
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # 验证
    sudo docker --version
    log_success "Docker 安装完成"
}

# 停止旧容器（如果存在）
cleanup_old() {
    if sudo docker ps -a --format '{{.Names}}' | grep -q "^warp$"; then
        log_warn "发现旧的 warp 容器，正在清理..."
        sudo docker stop warp 2>/dev/null || true
        sudo docker rm warp 2>/dev/null || true
        log_success "旧容器已清理"
    fi
}

# 安装 WARP（Docker 方案）
install_warp_docker() {
    log_info "拉取 WARP Docker 镜像..."
    sudo docker pull victronenergy/cloudflare-warp:latest
    
    log_info "启动 WARP 容器..."
    sudo docker run -d \
        --name warp \
        --restart=always \
        --cap-add NET_ADMIN \
        --device /dev/net/tun \
        -p 1080:1080 \
        victronenergy/cloudflare-warp:latest
    
    log_success "WARP 容器已启动"
}

# 等待 WARP 初始化
wait_for_warp() {
    log_info "等待 WARP 初始化（最多 30 秒）..."
    local max_attempts=6
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if sudo docker exec warp warp-cli status &> /dev/null; then
            log_success "WARP daemon 已就绪"
            return 0
        fi
        echo -n "."
        sleep 5
        ((attempt++))
    done
    
    log_error "WARP 初始化超时"
    log_info "查看容器日志：sudo docker logs warp"
    exit 1
}

# 注册并连接 WARP
register_warp() {
    log_info "注册 WARP..."
    sudo docker exec warp warp-cli registration new
    
    log_info "设置代理模式..."
    sudo docker exec warp warp-cli set-mode proxy
    
    log_info "连接 WARP..."
    sudo docker exec warp warp-cli connect
    
    log_success "WARP 注册并连接完成"
}

# 验证 WARP 状态
verify_warp() {
    log_info "验证 WARP 状态..."
    echo ""
    sudo docker exec warp warp-cli status
    echo ""
    
    log_info "测试出口 IP（应该显示 Cloudflare IP）..."
    local ip_info=$(sudo docker exec warp curl -s -x socks5://127.0.0.1:1080 https://ipinfo.io)
    echo "$ip_info" | grep -E "ip|org"
    
    if echo "$ip_info" | grep -q "cloudflare\|Cloudflare"; then
        log_success "✅ WARP 工作正常！出口 IP 是 Cloudflare"
    else
        log_warn "⚠️  出口 IP 可能不是 Cloudflare，请检查"
    fi
}

# 安装 Python + Telethon（可选）
install_python() {
    log_info "检查 Python 环境..."
    if ! command -v python3 &> /dev/null; then
        log_info "安装 Python3..."
        sudo apt install -y python3 python3-pip
    fi
    
    log_info "安装 Telethon..."
    sudo pip3 install telethon --break-system-packages
    log_success "Python + Telethon 安装完成"
}

# 生成 Telegram Session 生成脚本
generate_session_script() {
    log_info "生成 Telegram Session 生成脚本..."
    
    sudo bash -c 'cat > /home/ubuntu/generate_session.py << EOF
import asyncio
from telethon import TelegramClient

# ============ 在这里填写你的 API 凭证 ============
api_id = 12345678  # 替换成你的 api_id（数字）
api_hash = "your_api_hash_here"  # 替换成你的 api_hash（字符串）
phone = "+8613812345678"  # 替换成你的手机号
# =================================================

async def main():
    # 使用 WARP SOCKS5 代理（Docker 方案端口 1080）
    client = TelegramClient(
        "oracle_session",
        api_id,
        api_hash,
        proxy=("socks5", "127.0.0.1", 1080)  # Docker 方案：1080
    )
    
    await client.start(phone=phone)
    print("✅ Session 生成成功！")
    print(f"Session 文件: oracle_session.session")
    
    # 测试获取用户信息
    me = await client.get_me()
    print(f"登录用户: {me.first_name} (@{me.username})")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
EOF'
    
    sudo chown ubuntu:ubuntu /home/ubuntu/generate_session.py
    log_success "Session 生成脚本已创建: /home/ubuntu/generate_session.py"
    log_warn "请编辑脚本，填入你的 api_id、api_hash 和 phone"
}

# 打印使用说明
print_usage() {
    local public_ip=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "未知")
    
    echo ""
    echo "=========================================="
    log_success "🎉 Oracle Cloud + WARP 安装完成！"
    echo "=========================================="
    echo ""
    echo "📌 SOCKS5 代理信息："
    echo "   - 地址: <a href="http://127.0.0.1:1080">127.0.0.1:1080</a>  (本地通过 SSH 隧道)"
    echo "   - 地址: <a href="http://${public_ip}:1080">${public_ip}:1080</a>  (直接连接，需开放防火墙)"
    echo ""
    echo "📌 日常维护命令："
    echo "   - 查看状态:   sudo docker exec warp warp-cli status"
    echo "   - 重启 WARP:  sudo docker restart warp"
    echo "   - 查看日志:   sudo docker logs warp"
    echo "   - 停止 WARP:  sudo docker stop warp"
    echo "   - 启动 WARP:  sudo docker start warp"
    echo ""
    echo "📌 换 IP 命令（WARP 重新注册）："
    echo "   sudo docker exec warp warp-cli disconnect"
    echo "   sudo docker exec warp warp-cli registration new"
    echo "   sudo docker exec warp warp-cli connect"
    echo ""
    echo "📌 本地使用（SSH 隧道）："
    echo "   在本地电脑执行："
    echo "   ssh -i /path/to/key.key -N -D 1080 ubuntu@${public_ip}"
    echo ""
    echo "   然后在另一个终端测试："
    echo "   curl -x socks5://<a href="http://127.0.0.1:1080">127.0.0.1:1080</a> https://ipinfo.io"
    echo ""
    echo "📌 生成 Telegram Session："
    echo "   1. 编辑脚本: vim ~/generate_session.py"
    echo "   2. 填入 api_id、api_hash、phone"
    echo "   3. 运行: python3 ~/generate_session.py"
    echo "   4. 下载到本地: scp -i key ubuntu@${public_ip}:~/oracle_session.session ./"
    echo ""
    echo "=========================================="
    log_success "✅ 配置完成！"
    echo "=========================================="
}

# 主函数
main() {
    echo "=========================================="
    echo "  Oracle Cloud + WARP 一键安装脚本"
    echo "  版本: 2.0 (Docker 方案)"
    echo "=========================================="
    echo ""
    
    # 检查权限
    check_root
    
    # 检测系统
    local arch=$(detect_arch)
    local os_info=$(detect_os)
    log_info "系统架构: $arch"
    log_info "系统版本: $os_info"
    echo ""
    
    # 安装步骤
    install_deps
    install_docker
    cleanup_old
    install_warp_docker
    wait_for_warp
    register_warp
    verify_warp
    install_python
    generate_session_script
    
    # 打印使用说明
    print_usage
}

# 运行主函数
main "$@"
