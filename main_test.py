from media.sensor import *
from media.display import *
from media.media import *
import utime,ubinascii,ujson,usocket,_thread,network,gc
import time

AP_SSID = 'Silent-Speak'  # 热点名称
AP_KEY = '12345678'  # 至少8位密码

DISPLAY_WIDTH = 640  # 修改这个值改变宽度
DISPLAY_HEIGHT = 480  # 修改这个值改变高度


#http服务
def http_server():
    global img,imgLock,RunCamera,ssCNT

    img = None       #拍摄到的照片，多线程运行时防未赋值出错
    RunCamera = True #线程退出条件，比如按Key键3秒后修改此值即可关闭程序

    while img==None and RunCamera==True: #死等摄像头启动后赋值给img
        os.exitpoint()
        utime.sleep_ms(100)

    while RunCamera: #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
        os.exitpoint()

        try:
            print('\tCreate WiFi hotspot')
            ap = network.WLAN(network.AP_IF)

            if not ap.active():
                ap.active(True)

            # 等待热点激活
            max_wait = 10
            while max_wait > 0:
                if ap.active():
                    break
                max_wait -= 1
                utime.sleep(1)
            print("AP active:", ap.active())

            # 配置热点参数（使用默认IP 192.168.4.1）
            ap.config(ssid=AP_SSID, key=AP_KEY)
            print(f"\nSSID: {AP_SSID}\nPassword: {AP_KEY}")

            # 获取实际分配的IP
            IPaddress = ap.ifconfig()[0]
            Port = 80
            print(f"AP IP: {IPaddress}")

            # 创建socket（添加SO_REUSEADDR解决端口占用）
            s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
            s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)  # 关键修复

            ai = usocket.getaddrinfo(IPaddress, Port)
            addr = ai[0][-1]
            s.bind(addr)
            s.listen(1)  # 减少并发连接数
            s.settimeout(5.0)  # 设置超时防止永久阻塞

            print(f'HTTP server at {IPaddress}:{Port}')
        except Exception as e:
            print(f'Setup error: {e}')
            utime.sleep(5)
            continue

        while RunCamera: #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
            os.exitpoint()
            try:
                cl, addr = s.accept() #没能理解addr的表达方法，未见形如192.168.1.20的IPv4的地址数据
                ssCNT = 0 #本次成功发送的帧计数器清零，-------实测未超过4000帧就不通讯了---------------
                request = cl.recv(1024)
                if not request:
                    continue
                request_str = request.decode()

                #待改进：
                #        未对HTTP协议进行解析和应答，无法通过浏览器控制设备
                #        应使用形如 if 'GET /stream' in request_str:的命令解析HTTP指令
                #需要做的工作：
                #    作为遥控车/船/飞机，应该定义一个html框架，里面应包含以下内容：
                #        云台控制 6组：上/下/左/右/远/近，幅度(输入框+滚动条，与每个按钮对应)
                #        运动控制 4组：进/退/左/右，速度/幅度(输入框+滚动条，与每个按钮对应)
                #        视 频 框 3个：前摄/左摄/右摄
                #                    分辨率640x360（GC2093使用比例1920:1080，图像才无畸变）
                #                    K230支持的3个摄像头，也可分别为视觉、深度、热成像
                #    解析http协议的GET/POST命令，并执行相应的指令
                header =    "HTTP/1.1 200 OK\r\n" \
                            "Server: Tao\r\n" \
                            "Content-Type: multipart/x-mixed-replace;boundary=Tao\r\n" \
                            "Cache-Control: no-cache\r\n" \
                            "Pragma: no-cache\r\n\r\n"
                # ********* 这个http内容来自网友Tao **********
                cl.sendall(header)
            except Exception as e:
                print(f"\n\tHTTP错误：{e}")
                break

            #被前面的accept和recv阻塞了
            #   若无阻塞，下面的代码不需要单独做循环，至少可跟recv放进同一个循环里
            while RunCamera: #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
                os.exitpoint()
                try:
                    if imgLock.acquire(1,1): #申请img变量的锁，阻塞1秒
                        img_bytes = img.compress(quality=50)
                        imgLock.release()
                        # ********* 这个http内容来自网友Tao **********
                        header = f"--Tao\r\nContent-Type: image/jpeg\r\nContent-Length: {len(img_bytes)}\r\n\r\n"
                        #待改进
                        #   按图片格式推送jpeg图片
                        #   实际上按视频码流模式的帧率会高很多
                        #需要做的工作
                        #   按视频流格式编码，比如H265视频格式
                        #   打包进http协议里，发送给3个视频框
                        cl.sendall(header)
                        cl.sendall(img_bytes)

                        #摄像头0的推送
                        #摄像头1的推送

                        del img_bytes
                        gc.collect()
                    else:
                        print('img变量锁申请超时')
                except Exception as e:
                    #if b'[Errno 11] EAGAIN' in e:
                    if e.errno == 11:
                        print('\t-----Error 11-----')
                        break
                    else:
                        print(f"\n\tHTTP错误：{e}")
                        break
                utime.sleep_ms(100) #限制帧率不超过10，给其它线程留下CPU时间
                ssCNT += 1 #帧计数---------------------------
        try:
            cl.close()
        except:
            pass
        try:
            s.close()
        except:
            pass
        print('\t----- Restart HTTP server -----')
        utime.sleep(5) #等5秒，重启WiFi


#拍摄
#   定时拍摄照片到img变量
#   其它线程可以使用或修改img变量，获得图像能力
def th_Camera():
    global img,imgLock,RunCamera,ssCNT

    cam = Sensor(id=2, width=1280, height=960, fps=60)
    cam.reset()
    cam.set_framesize(
                chn=CAM_CHN_ID_0, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT
            )
    cam.set_pixformat(chn=CAM_CHN_ID_0, pix_format=Sensor.GRAYSCALE)

    # Display.init(Display.ST7701, to_ide=True, osd_num = 2)
    MediaManager.init()
    cam.run()

    RunCamera = True
    clock = time.clock()
    fps = 0
    ssCNT = 0 #计时------------------------------
    while RunCamera: #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
        clock.tick()
        os.exitpoint()
        if imgLock.acquire(1,1): #申请变量img的锁，阻塞1秒
            del img
            gc.collect()
            img = cam.snapshot()
            #img.draw_string_advanced(5,5,36,'%d fps: %.1f'%(ssCNT,fps),color=(255,0,0))
            imgLock.release()
        utime.sleep_ms(50) #为保证数据及时刷新，2倍于推送帧率
        fps = clock.fps()
    cam.stop()
    utime.sleep_ms(100)
    MediaManager.deinit()

#显示，其它线程可以修改img变量获得显示能力
def th_Display():
    global img,imgLock,RunCamera

    RunCamera = True #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
    img = None
    while img == None and RunCamera==True: #死等摄像头启动后赋值给img
        os.exitpoint()
        utime.sleep_ms(100)

    while RunCamera: #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
        os.exitpoint()
        if imgLock.acquire(0,0):#申请变量img的锁，无阻塞
            Display.show_image(img,x=80,y=60) #显示图片
            #显示摄像头0的图像
            #显示摄像头1的图像
            imgLock.release()
        utime.sleep_ms(100)


if __name__ == "__main__":
    global RunCamera

    RunCamera = True #线程退出条件，比如按Key键3秒后修改此值即可关闭程序
    imgLock = _thread.allocate_lock() #线程锁实例

    _thread.start_new_thread(th_Camera, ())   #摄像头线程
    #_thread.start_new_thread(th_Display, ())  #显示线程
    _thread.start_new_thread(http_server, ()) #推流线程
    while RunCamera:
        os.exitpoint()
        utime.sleep(1)
