from media.vencoder import *
from media.sensor import *
from media.media import *
import time, os
import _thread
import multimedia as mm
from time import *


import network
import time

AP_SSID = 'Silent-Speak'  # 热点名称
AP_KEY = '12345678'  # 至少8位密码

def ap_init():
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

class RtspServer:
    def __init__(self, session_name="test", port=8554, video_type=mm.multi_media_type.media_h264, enable_audio=False):
        self.session_name = session_name  # 会话名称
        self.video_type = video_type        # 视频编码类型（ H264/H265 ）
        self.enable_audio = enable_audio    # 是否启用音频
        self.port = port                    # RTSP 服务器端口号
        self.rtspserver = mm.rtsp_server()  # 实例化 RTSP 服务器
        self.venc_chn = VENC_CHN_ID_0       # 视频编码通道
        self.start_stream = False            # 是否启动推流线程
        self.runthread_over = False          # 推流线程是否结束

    def start(self):
        # 初始化推流
        self._init_stream()
        self.rtspserver.rtspserver_init(self.port)
        # 创建会话
        self.rtspserver.rtspserver_createsession(self.session_name, self.video_type, self.enable_audio)
        # 启动 RTSP 服务器
        self.rtspserver.rtspserver_start()
        self._start_stream()

        # 启动推流线程
        self.start_stream = True
        _thread.start_new_thread(self._do_rtsp_stream, ())

    def stop(self):
        if not self.start_stream:
            return
        # 等待推流线程退出
        self.start_stream = False
        while not self.runthread_over:
            sleep(0.1)
        self.runthread_over = False

        # 停止推流
        self._stop_stream()
        self.rtspserver.rtspserver_stop()
        self.rtspserver.rtspserver_deinit()

    def get_rtsp_url(self):
        return self.rtspserver.rtspserver_getrtspurl(self.session_name)

    def _init_stream(self):
        width = 1280
        height = 720
        width = ALIGN_UP(width, 16)
        # 初始化传感器
        self.sensor = Sensor()
        self.sensor.reset()
        self.sensor.set_framesize(width=width, height=height, alignment=12)
        self.sensor.set_pixformat(Sensor.YUV420SP)
        # 实例化 video encoder
        self.encoder = Encoder()
        self.encoder.SetOutBufs(self.venc_chn, 8, width, height)
        # 绑定 camera 和 venc
        self.link = MediaManager.link(self.sensor.bind_info()['src'], (VIDEO_ENCODE_MOD_ID, VENC_DEV_ID, self.venc_chn))
        # init media manager
        MediaManager.init()
        # 创建编码器
        chnAttr = ChnAttrStr(self.encoder.PAYLOAD_TYPE_H264, self.encoder.H264_PROFILE_MAIN, width, height)
        self.encoder.Create(self.venc_chn, chnAttr)

    def _start_stream(self):
        # 开始编码
        self.encoder.Start(self.venc_chn)
        # 启动 camera
        self.sensor.run()

    def _stop_stream(self):
        # 停止 camera
        self.sensor.stop()
        # 接绑定 camera 和 venc
        del self.link
        # 停止编码
        self.encoder.Stop(self.venc_chn)
        self.encoder.Destroy(self.venc_chn)
        # 清理 buffer
        MediaManager.deinit()

    def _do_rtsp_stream(self):
        try:
            streamData = StreamData()
            while self.start_stream:
                os.exitpoint()
                # 获取一帧码流
                self.encoder.GetStream(self.venc_chn, streamData)
                # 推流
                for pack_idx in range(0, streamData.pack_cnt):
                    stream_data = bytes(uctypes.bytearray_at(streamData.data[pack_idx], streamData.data_size[pack_idx]))
                    self.rtspserver.rtspserver_sendvideodata(self.session_name,stream_data, streamData.data_size[pack_idx],1000)
                    #print("stream size: ", streamData.data_size[pack_idx], "stream type: ", streamData.stream_type[pack_idx])
                # 释放一帧码流
                self.encoder.ReleaseStream(self.venc_chn, streamData)

        except BaseException as e:
            print(f"Exception {e}")
        finally:
            self.runthread_over = True
            # 停止 rtsp server
            self.stop()

        self.runthread_over = True

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    #ap_init()
    sleep(10)
    # 创建 rtsp server 对象
    rtspserver = RtspServer()
    # 启动 rtsp server
    rtspserver.start()
    # 打印 rtsp url
    print("rtsp server start:",rtspserver.get_rtsp_url())
    # 推流 60s
    sleep(600)
    # 停止 rtsp server
    rtspserver.stop()
    print("done")
