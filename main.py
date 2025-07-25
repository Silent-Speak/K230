import utime, ubinascii, ujson, usocket, _thread, network, gc
import time
from media.sensor import *
from media.display import *
from media.media import *
time.sleep(5) #等待WiFi模块初始化
# 全局变量
img = None  # 拍摄到的照片
RunCamera = True  # 线程退出标志
ssCNT = 0  # 帧计数
gc_threshold = 200  # 每发送200张图像进行一次垃圾回收

SSID = 'HUAWEI-72E9'
PASSWORD = 'abcd5678'

def network_use_wlan(is_wlan=True):
    if is_wlan:
        sta=network.WLAN(0)
        sta.connect(SSID, PASSWORD)
        print(sta.status())
        while sta.ifconfig()[0] == '0.0.0.0':
            os.exitpoint()
        print(sta.ifconfig())
        ip = sta.ifconfig()[0]
        return ip
    else:
        a=network.LAN()
        if not a.active():
            raise RuntimeError("LAN interface is not active.")
        a.ifconfig("dhcp")
        print(a.ifconfig())
        ip = a.ifconfig()[0]
        return ip

# HTTP服务
def http_server():
    global img, RunCamera, ssCNT, gc_threshold

    # 连接网络，获取IP地址
    IPaddress = network_use_wlan()
    Port = 80
    ai = usocket.getaddrinfo(IPaddress, Port)
    addr = ai[0][-1]
    print(f'\tCreate HTTP server listen at {IPaddress}:{Port}\n\n')

    # 创建 HTTP 服务器
    s = usocket.socket()
    s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)

    while RunCamera:
        try:
            while True:
                try:
                    cl, addr = s.accept()
                    break
                except Exception as e:
                    print({e})
                    print("等待连接")
                    time.sleep(0.5)
            print(f"Client connected from {addr}")
#            request = cl.recv(1024)
#            if not request:
#                continue
#            request_str = request.decode()
            header = "HTTP/1.1 200 OK\r\n" \
                     "Server: Tao\r\n" \
                     "Content-Type: multipart/x-mixed-replace;boundary=Tao\r\n" \
                     "Cache-Control: no-cache\r\n" \
                     "Pragma: no-cache\r\n\r\n"
            print(1)
            cl.send(header.encode())
            print(2)

            while RunCamera:
                try:
                    if img is not None:  # 检查img是否为None
                        img_bytes = img.compress(quality=50)
                        header = f"--Tao\r\nContent-Type: image/jpeg\r\nContent-Length: {len(img_bytes)}\r\n\r\n"
                        cl.send(header.encode())
                        cl.send(img_bytes)

                        del img_bytes
                        if ssCNT % gc_threshold == 0:
                            gc.collect()
                            print(f"Garbage collected at frame {ssCNT}")
                    else:
                        print('img变量为None')
                except Exception as e:
                    if e.errno == 11:
                        print('\t-----Error 11-----')
                        break
                    else:
                        print(f"\n\tHTTP错误：{e}")
                        break
                utime.sleep_ms(30)  # 限制帧率
                ssCNT += 1  # 帧计数
        except Exception as e:
            print(f"\n\t建立HTTP服务时出错：{e}")
            cl.close()
            s.close()
            ap.active(False)
            utime.sleep(5)  # 等5秒，重启WiFi
            s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
            s.bind(addr)
            s.listen(5)
        finally:
            cl.close()
            utime.sleep(1)  # 等1秒，确保所有数据都已发送完毕

# 拍摄
def th_Camera():
    global img, RunCamera, ssCNT

    cam = Sensor(id=2, width=1280, height=720, fps=90)
    cam.reset()
    cam.set_framesize(width=640, height=480, chn=CAM_CHN_ID_0)
    cam.set_pixformat(Sensor.GRAYSCALE, chn=CAM_CHN_ID_0)

    MediaManager.init()
    cam.run()

    clock = time.clock()
    fps = 0

    while RunCamera:
        clock.tick()
        del img
        gc.collect()
        img = cam.snapshot()
        # 只显示帧数，不显示FPS
        img.draw_string_advanced(5, 5, 36, f'{ssCNT}', color=(255, 0, 0))
        utime.sleep_ms(15)  # 为保证数据及时刷新，2倍于推送帧率
        fps = clock.fps()
        # 在控制台打印FPS
        print(f'当前FPS: {fps:.1f}')
    cam.stop()
    utime.sleep_ms(30)
    MediaManager.deinit()


if __name__ == "__main__":
    RunCamera = True  # 线程退出条件，比如按Key键3秒后修改此值即可关闭程序

    _thread.start_new_thread(th_Camera, ())   # 摄像头线程
    _thread.start_new_thread(http_server, ()) # 推流线程

    while RunCamera:
        utime.sleep(1)
