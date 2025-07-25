import network
import time, os, select, struct
from media.sensor import *
from media.display import *
from media.media import *
from machine import Timer
from cl import PC_Discoverer
from g1lib import StreamSender
from vofa_lite import JustFloatHandler
from StreamServer import MjpegServer


AP_SSID = 'Silent-Speak'  # 热点名称
AP_KEY = '12345678'  # 至少8位密码

STREAM_WIDTH = 640  # 修改这个值改变宽度
STREAM_HEIGHT = 480  # 修改这个值改变高度

PORT=8015

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

def closeCamera():
    try:
        if "sender" in locals():
            sender.close()
    except:
        pass
    if "sensor" in locals() and isinstance(sensor, Sensor):
        sensor.stop()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()

def streaming():
        cfg = ConfigStore.model_validate_json(s_config.value)
        shape = (STREAM_HEIGHT,
                 STREAM_WIDTH,
                 1)
        # start stream server
        stream_server = MjpegServer()
        stream_server.start(PORT)
        image=sensor.snapshot(chn=CAM_CHN_ID_0)
        while True:
            try:
                stream_server.set_frame(image)
                cnt = 0
            except Exception as e:
                logger.exception(e)
if __name__ == "__main__":
    ap_test()

    sensor = Sensor(id=2, width=1280, height=960, fps=60)
    sensor.reset()
    sensor.set_framesize(
                chn=CAM_CHN_ID_0, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT
            )
    sensor.set_pixformat(chn=CAM_CHN_ID_0, pix_format=Sensor.GRAYSCALE)
    sensor.run()

    while True:
        streaming()
