# Description: This example demonstrates how to stream video and audio to the network using the RTSP server.
#
# Note: You will need an SD card to run this example.
#
# You can run the rtsp server to stream video and audio to the network

import network
import time
import os
import _thread
from time import sleep
import multimedia as mm

from media.vencoder import *
from media.sensor import *
from media.media import *


SSID = "HUAWEI-72E9"        # 路由器名称
PASSWORD = "abcd5678" # 路由器密码

DISPLAY_WIDTH = 640  # 修改这个值改变宽度
DISPLAY_HEIGHT = 480  # 修改这个值改变高度


def sta_test():
    # 初始化STA模式（客户端模式）
    sta = network.WLAN(network.STA_IF)

    # 激活WiFi模块（相当于打开手机WIFI开关）
    if not sta.active():  # 判断是否已激活
        sta.active(True)
    print("WiFi模块激活状态:", sta.active())

    # 查看初始连接状态
    print("初始连接状态:", sta.status())

    # 扫描当前环境中的WIFI
    wifi_list = sta.scan()  # 扫描周围WiFi
    # 打印每个Wi-Fi信息
    for wifi in wifi_list:
        # 访问 rt_wlan_info 对象的属性
        ssid = wifi.ssid       # ssid 属性
        rssi = wifi.rssi       # rssi 属性
        print(f"SSID: {ssid}, 信号强度: {rssi}dBm")

    # 尝试连接路由器
    print(f"正在连接 {SSID}...")
    sta.connect(SSID, PASSWORD)

    # 等待连接结果（最多尝试5次）
    max_wait = 5
    while max_wait > 0:
        if sta.isconnected():  # 检查是否连接成功
            break
        max_wait -= 1
        time.sleep(1)  # 失败了就线休息一秒再说
        sta.connect(SSID, PASSWORD)
        print("剩余等待次数：", max_wait, "次")

    # 如果获取不到IP地址就一直在这等待
    while sta.ifconfig()[0] == '0.0.0.0':
        pass

    if sta.isconnected():
        print("\n连接成功！")
        # 重新获取并打印网络配置
        ip_info = sta.ifconfig()
        print(f"IP地址: {ip_info[0]}")
        print(f"子网掩码: {ip_info[1]}")
        print(f"网关: {ip_info[2]}")
        print(f"DNS服务器: {ip_info[3]}")
    else:
        print("连接失败，请检查密码或信号强度")


class RtspServer:
    def __init__(
        self,
        session_name="test",
        port=8554,
        video_type=mm.multi_media_type.media_h264,
        enable_audio=False
    ):
        self.session_name = session_name  # Session name
        self.video_type = video_type     # Video type: H264/H265
        self.enable_audio = enable_audio  # Enable audio streaming
        self.port = port                  # RTSP port number

        self.rtspserver = mm.rtsp_server()  # RTSP server instance
        self.venc_chn = VENC_CHN_ID_0       # Video encoder channel

        self.start_stream = False  # Stream thread running flag
        self.runthread_over = False  # Stream thread completion flag

    def start(self):
        # Initialize streaming components
        self._init_stream()

        # Initialize RTSP server
        self.rtspserver.rtspserver_init(self.port)
        # Create RTSP session
        self.rtspserver.rtspserver_createsession(
            self.session_name,
            self.video_type,
            self.enable_audio
        )
        # Start RTSP server
        self.rtspserver.rtspserver_start()

        # Start media streaming
        self._start_stream()

        # Start streaming thread
        self.start_stream = True
        _thread.start_new_thread(self._do_rtsp_stream, ())

    def stop(self):
        if not self.start_stream:
            return

        # Signal thread to stop
        self.start_stream = False
        # Wait for thread to exit
        while not self.runthread_over:
            sleep(0.1)
        self.runthread_over = False

        # Stop media streaming
        self._stop_stream()

        # Stop RTSP server
        self.rtspserver.rtspserver_stop()
        # self.rtspserver.rtspserver_destroysession(self.session_name)
        self.rtspserver.rtspserver_deinit()

    def get_rtsp_url(self):
        return self.rtspserver.rtspserver_getrtspurl(self.session_name)

    def _init_stream(self):
        width = 1280
        height = 720
        width = ALIGN_UP(width, 16)

        # Initialize sensor
        self.sensor = Sensor(id=2, width=1280, height=960, fps=60)
        self.sensor.reset()
        self.sensor.set_framesize(
                    chn=CAM_CHN_ID_0, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT
                )
        self.sensor.set_pixformat(chn=CAM_CHN_ID_0, pix_format=Sensor.GRAYSCALE)

        # Initialize video encoder
        self.encoder = Encoder()
        self.encoder.SetOutBufs(self.venc_chn, 8, width, height)

        # Create media link
        self.link = MediaManager.link(
            self.sensor.bind_info()['src'],
            (VIDEO_ENCODE_MOD_ID, VENC_DEV_ID, self.venc_chn)
        )

        # Initialize media manager
        MediaManager.init()

        # Create encoder channel
        chnAttr = ChnAttrStr(
            self.encoder.PAYLOAD_TYPE_H264,
            self.encoder.H264_PROFILE_MAIN,
            width,
            height
        )
        self.encoder.Create(self.venc_chn, chnAttr)

    def _start_stream(self):
        # Start encoder
        self.encoder.Start(self.venc_chn)
        # Start camera sensor
        self.sensor.run()

    def _stop_stream(self):
        # Stop camera sensor
        self.sensor.stop()
        # Remove media link
        del self.link
        # Stop encoder
        self.encoder.Stop(self.venc_chn)
        self.encoder.Destroy(self.venc_chn)
        # Deinitialize media manager
        MediaManager.deinit()

    def _do_rtsp_stream(self):
        try:
            streamData = StreamData()
            while self.start_stream:
                os.exitpoint()

                # Get encoded stream frame
                self.encoder.GetStream(self.venc_chn, streamData)

                # Push each packet in the frame
                for pack_idx in range(0, streamData.pack_cnt):
                    stream_data = bytes(uctypes.bytearray_at(
                        streamData.data[pack_idx],
                        streamData.data_size[pack_idx]
                    ))
                    self.rtspserver.rtspserver_sendvideodata(
                        self.session_name,
                        stream_data,
                        streamData.data_size[pack_idx],
                        1000
                    )
                    # Debug print (optional)
                    # print(f"stream size: {streamData.data_size[pack_idx]}, type: {streamData.stream_type[pack_idx]}")

                # Release the stream frame
                self.encoder.ReleaseStream(self.venc_chn, streamData)

        except BaseException as e:
            print(f"Exception: {e}")
        finally:
            self.runthread_over = True
            # Ensure clean stop if exception occurs
            self.stop()


if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)

    sta_test()

    # Create and start RTSP server
    rtspserver = RtspServer()
    rtspserver.start()

    # Display streaming URL
    print("RTSP server started:", rtspserver.get_rtsp_url())

    # Stream indefinitely
    try:
        while True:
            sleep(60)
    finally:
        # Stop server on exit
        rtspserver.stop()
        print("RTSP server stopped")
