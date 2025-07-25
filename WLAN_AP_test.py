# 立创·庐山派-K230-CanMV开发板资料与相关扩展板软硬件资料官网全部开源
# 开发板官网：www.lckfb.com
# 技术支持常驻论坛，任何技术问题欢迎随时交流学习
# 立创论坛：www.jlc-bbs.com/lckfb
# 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
# 不靠卖板赚钱，以培养中国工程师为己任

import network
import time

AP_SSID = 'LushanPi-AP'  # 热点名称
AP_KEY = '123456781'  # 至少8位密码

def ap_test():
    # 初始化AP模式
    ap = network.WLAN(network.AP_IF)

    # 激活AP模式
    if not ap.active():
        ap.active(True)
    print("AP模式激活状态:", ap.active())

    # 配置热点参数
    ap.config(ssid=AP_SSID,key=AP_KEY)
    print("\n热点已创建:")
    print(f"SSID: {AP_SSID}")
    print(f"Channel: {AP_KEY}")

    # 等待热点启动（暂定3秒）
    time.sleep(3)

    # 获取并打印IP信息
    ip_info = ap.ifconfig()
    print("\nAP网络配置:")
    print(f"IP地址: {ip_info[0]}")
    print(f"子网掩码: {ip_info[1]}")
    print(f"网关: {ip_info[2]}")
    print(f"DNS服务器: {ip_info[3]}")

    # 持续监控连接设备
    while True:
        clients = ap.status('stations')
        print(f"\n已连接设备数: {len(clients)}")

        time.sleep(1)

ap_test()
