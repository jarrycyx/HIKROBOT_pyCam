# -- coding: utf-8 --
import sys
from tkinter import *
from tkinter.messagebox import *
import _tkinter
import tkinter.messagebox
import tkinter as tk
from tkinter import ttk
# sys.path.append("./MvImport")
from MvImport.MvCameraControl_class import *
from CamOperation_class import *
from PIL import Image, ImageTk
import threading

import Utils as U


# DEFAULT_TRIGGER = 'triggermode'

EXP_TIME = 1000
EXP_GAIN = 20
FRAME_RATE = 15
DEFAULT_TRIGGER = 'continuous'


if __name__ == "__main__":
    global deviceList
    deviceList = MV_CC_DEVICE_INFO_LIST()
    global tLayerType
    tLayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
    global obj_cam_operation
    obj_cam_operation = 0
    global b_is_run
    b_is_run = False
    global nOpenDevSuccess
    nOpenDevSuccess = 0
    global devList

    # 界面设计代码
    window = tk.Tk()
    window.title('Multiple Cameras Burst: Support BMP & TIFF')
    window.geometry('1330x1020')
    model_val = tk.StringVar()
    global triggercheck_val
    triggercheck_val = tk.IntVar()
    page = Frame(window, height=400, width=60)
    page.pack(expand=True, fill=BOTH)
    panel = Label(page)
    panel.place(x=300, y=10, height=500, width=500)

    panel1 = Label(page)
    panel1.place(x=810, y=10, height=500, width=500)

    panel2 = Label(page)
    panel2.place(x=300, y=520, height=500, width=500)

    panel3 = Label(page)
    panel3.place(x=810, y=520, height=500, width=500)

    panels = [panel, panel1, panel2, panel3]


    # ch:枚举相机 | en:enum devices
    def enum_devices():
        global deviceList
        global devList
        deviceList = MV_CC_DEVICE_INFO_LIST()
        tLayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
        ret = MvCamera.MV_CC_EnumDevices(tLayerType, deviceList)
        if ret != 0:
            tkinter.messagebox.showerror('show error', 'enum devices fail! ret = ' + U.ToHexStr(ret))

        # 显示相机个数
        text_number_of_devices.delete(1.0, tk.END)
        text_number_of_devices.insert(1.0, str(deviceList.nDeviceNum))

        if deviceList.nDeviceNum == 0:
            tkinter.messagebox.showinfo('show info', 'find no device!')

        U.print_log("Find %d devices!" % deviceList.nDeviceNum)

        devList = []
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                U.print_log("\ngige device: [%d]" % i)
                strModeName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName:
                    strModeName = strModeName + chr(per)
                U.print_log("device model name: %s" % strModeName)

                nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                U.print_log("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
                devList.append(
                    "Gige[" + str(i) + "]:" + str(nip1) + "." + str(nip2) + "." + str(nip3) + "." + str(nip4))
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                U.print_log("\nu3v device: [%d]" % i)
                strModeName = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName:
                    if per == 0:
                        break
                    strModeName = strModeName + chr(per)
                U.print_log("device model name: %s" % strModeName)

                strSerialNumber = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber:
                    if per == 0:
                        break
                    strSerialNumber = strSerialNumber + chr(per)
                U.print_log("user serial number: %s" % strSerialNumber)
                devList.append("USB[" + str(i) + "]" + str(strSerialNumber))

        # ch:打开相机 | en:open device


    def open_device():
        global deviceList
        global obj_cam_operation
        global b_is_run
        global nOpenDevSuccess
        nOpenDevSuccess = 0
        global devList
        if b_is_run:
            tkinter.messagebox.showinfo('show info', 'Camera is Running!')
            return
        obj_cam_operation = []
        for i in range(0, deviceList.nDeviceNum):
            camObj = MvCamera()
            strName = str(devList[i])
            obj_cam_operation.append(CameraOperation(camObj, deviceList, i, cam_name=strName))
            ret = obj_cam_operation[nOpenDevSuccess].Open_device()
            if 0 != ret:
                obj_cam_operation.pop()
                continue
            else:
                U.print_log(str(devList[i]))
                nOpenDevSuccess = nOpenDevSuccess + 1
                model_val.set(DEFAULT_TRIGGER)
                # start_grabbing()
            if 4 == nOpenDevSuccess:
                b_is_run = True
                break
            U.print_log("nOpenDevSuccess = ", nOpenDevSuccess)

            # ch:开始取流 | en:Start grab image


    def start_grabbing():
        global obj_cam_operation
        global nOpenDevSuccess
        lock = threading.Lock()  # 申请一把锁
        ret = 0
        threads = []

        for i in range(0, nOpenDevSuccess):
            # ret = obj_cam_operation[i].Start_grabbing(i, window, panels[i], lock)
            # if 0 != ret:
            #     tkinter.messagebox.showerror('show error',
            #                                  'camera:' + str(i) + ',start grabbing fail! ret = ' + U.To_hex_str(ret))

            start_grabbing_thread = threading.Thread(target=obj_cam_operation[i].Start_grabbing, args=(i, window, panels[i], lock))
            start_grabbing_thread.start()
            threads.append(start_grabbing_thread)

        for t in threads:
            t.join()


    # ch:停止取流 | en:Stop grab image
    def stop_grabbing():
        global nOpenDevSuccess
        global obj_cam_operation
        for i in range(0, nOpenDevSuccess):
            ret = obj_cam_operation[i].Stop_grabbing()
            if 0 != ret:
                tkinter.messagebox.showerror('show error',
                                             'camera:' + str(i) + 'stop grabbing fail!ret = ' + U.To_hex_str(ret))


    # ch:关闭设备 | Close device
    def close_device():
        global b_is_run
        global obj_cam_operation
        global nOpenDevSuccess
        for i in range(0, nOpenDevSuccess):
            ret = obj_cam_operation[i].Close_device()
            if 0 != ret:
                tkinter.messagebox.showerror('show error',
                                             'camera:' + str(i) + 'close deivce fail!ret = ' + U.To_hex_str(ret))
                b_is_run = True
                return
        b_is_run = False
        # 清除文本框的数值
        text_frame_rate.delete(1.0, tk.END)
        text_exposure_time.delete(1.0, tk.END)
        text_gain.delete(1.0, tk.END)


    # ch:设置触发模式 | en:set trigger mode
    def set_triggermode():
        global obj_cam_operation
        global nOpenDevSuccess
        strMode = model_val.get()
        U.print_log(strMode)
        for i in range(0, nOpenDevSuccess):
            ret = obj_cam_operation[i].Set_trigger_mode(strMode)
            if 0 != ret:
                tkinter.messagebox.showerror('show error',
                                             'camera:' + str(i) + 'set triggersource fail!ret = ' + U.To_hex_str(ret))


    # ch:设置触发命令 | en:set trigger software
    def trigger_once():
        global triggercheck_val
        global obj_cam_operation
        global nOpenDevSuccess
        nCommand = triggercheck_val.get()
        for i in range(0, nOpenDevSuccess):
            ret = obj_cam_operation[i].Trigger_once(nCommand)
            if 0 != ret:
                tkinter.messagebox.showerror('show error',
                                             'camera:' + str(i) + 'set triggersoftware fail!ret = ' + U.To_hex_str(ret))


    def get_parameter():
        global obj_cam_operation
        global nOpenDevSuccess
        for i in range(0, nOpenDevSuccess):
            ret = obj_cam_operation[i].Get_parameter()
            if 0 != ret:
                tkinter.messagebox.showerror('show error',
                                             'camera' + str(i) + 'get parameter fail!ret = ' + U.To_hex_str(ret))
            text_frame_rate.delete(1.0, tk.END)
            text_frame_rate.insert(1.0, obj_cam_operation[i].frame_rate)
            text_exposure_time.delete(1.0, tk.END)
            text_exposure_time.insert(1.0, obj_cam_operation[i].exposure_time)
            text_gain.delete(1.0, tk.END)
            text_gain.insert(1.0, obj_cam_operation[i].gain)


    def set_parameter():
        global obj_cam_operation
        global nOpenDevSuccess
        for i in range(0, nOpenDevSuccess):
            obj_cam_operation[i].exposure_time = text_exposure_time.get(1.0, tk.END)
            obj_cam_operation[i].exposure_time = obj_cam_operation[i].exposure_time.rstrip("\n")
            obj_cam_operation[i].gain = text_gain.get(1.0, tk.END)
            obj_cam_operation[i].gain = obj_cam_operation[i].gain.rstrip("\n")
            obj_cam_operation[i].frame_rate = text_frame_rate.get(1.0, tk.END)
            obj_cam_operation[i].frame_rate = obj_cam_operation[i].frame_rate.rstrip("\n")
            ret = obj_cam_operation[i].Set_parameter(obj_cam_operation[i].frame_rate,
                                                     obj_cam_operation[i].exposure_time, obj_cam_operation[i].gain)
            if 0 != ret:
                tkinter.messagebox.showerror('show error', 'camera' + str(i) + 'set parameter fail!')


    # ch:保存bmp图片 | en:save bmp image
    def bmp_save():
        global obj_cam_operation
        for i in range(0, nOpenDevSuccess):
            obj_cam_operation[i].b_save_bmp = True
            obj_cam_operation[i].burst = False


    # ch:保存TIF图片 | en:save TIF image
    def tif_save():
        global obj_cam_operation
        for i in range(0, nOpenDevSuccess):
            obj_cam_operation[i].b_save_tif = True
            obj_cam_operation[i].burst = False


    # ch:保存bmp图片序列 | en:save bmp image
    def sequence_start():
        stop_grabbing()
        start_grabbing()
        global obj_cam_operation
        for i in range(0, nOpenDevSuccess):
            obj_cam_operation[i].b_save_tif = True
            obj_cam_operation[i].burst = True


    # ch:停止bmp序列采集 | en:save jpg image
    def sequence_stop():
        global obj_cam_operation
        for i in range(0, nOpenDevSuccess):
            obj_cam_operation[i].b_save_tif = False
            obj_cam_operation[i].burst = False


    def quick_start():
        enum_devices()
        open_device()
        start_grabbing()
        text_exposure_time.delete("1.0", tk.END)
        text_gain.delete("1.0", tk.END)
        text_frame_rate.delete("1.0", tk.END)

        text_exposure_time.insert("1.0", EXP_TIME)
        text_gain.insert("1.0", EXP_GAIN)
        text_frame_rate.insert("1.0", FRAME_RATE)
        set_parameter()
        # start_grabbing()


    text_number_of_devices = tk.Text(window, width=10, height=1)
    text_number_of_devices.place(x=200, y=20)
    label_total_devices = tk.Label(window, text='Number of camera：', width=25, height=1)
    label_total_devices.place(x=20, y=20)

    label_exposure_time = tk.Label(window, text='Exposure Time', width=15, height=1)
    label_exposure_time.place(x=20, y=400)
    text_exposure_time = tk.Text(window, width=15, height=1)
    text_exposure_time.place(x=160, y=400)

    label_gain = tk.Label(window, text='Gain', width=15, height=1)
    label_gain.place(x=20, y=450)
    text_gain = tk.Text(window, width=15, height=1)
    text_gain.place(x=160, y=450)

    label_frame_rate = tk.Label(window, text='Frame Rate', width=15, height=1)
    label_frame_rate.place(x=20, y=500)
    text_frame_rate = tk.Text(window, width=15, height=1)
    text_frame_rate.place(x=160, y=500)

    btn_enum_devices = tk.Button(window, text='Initialization Cameras', width=35, height=1, command=enum_devices)
    btn_enum_devices.place(x=20, y=50)
    btn_open_device = tk.Button(window, text='Open Device', width=15, height=1, command=open_device)
    btn_open_device.place(x=20, y=100)
    btn_close_device = tk.Button(window, text='Close Device', width=15, height=1, command=close_device)
    btn_close_device.place(x=160, y=100)

    btn_save_bmp = tk.Button(window, text='Save BMP', width=15, height=1, command=bmp_save)
    btn_save_bmp.place(x=20, y=300)
    btn_save_jpg = tk.Button(window, text='Save TIFF', width=15, height=1, command=tif_save)
    btn_save_jpg.place(x=160, y=300)

    btn_save_bmp = tk.Button(window, text='Burst Start', width=15, height=1, command=sequence_start)
    btn_save_bmp.place(x=20, y=350)
    btn_save_jpg = tk.Button(window, text='Burst Stop', width=15, height=1, command=sequence_stop)
    btn_save_jpg.place(x=160, y=350)

    model_val.set(0)
    radio_continuous = tk.Radiobutton(window, text='Continuous', variable=model_val, value='continuous', width=15,
                                      height=1, command=set_triggermode)
    radio_continuous.place(x=20, y=150)
    radio_trigger = tk.Radiobutton(window, text='Trigger Mode', variable=model_val, value='triggermode', width=15,
                                   height=1, command=set_triggermode)
    radio_trigger.place(x=160, y=150)

    btn_start_grabbing = tk.Button(window, text='Start Grabbing', width=15, height=1, command=start_grabbing)
    btn_start_grabbing.place(x=20, y=200)
    btn_stop_grabbing = tk.Button(window, text='Stop Grabbing', width=15, height=1, command=stop_grabbing)
    btn_stop_grabbing.place(x=160, y=200)

    checkbtn_trigger_software = tk.Checkbutton(window, text='Tigger by Software', variable=triggercheck_val, onvalue=1,
                                               offvalue=0)
    checkbtn_trigger_software.place(x=20, y=250)
    btn_trigger_once = tk.Button(window, text='Trigger Once', width=15, height=1, command=trigger_once)
    btn_trigger_once.place(x=160, y=250)
    triggercheck_val.set(True)

    btn_get_parameter = tk.Button(window, text='Get Parameter', width=15, height=1, command=get_parameter)
    btn_get_parameter.place(x=20, y=550)
    btn_set_parameter = tk.Button(window, text='Set Parameter', width=15, height=1, command=set_parameter)
    btn_set_parameter.place(x=160, y=550)

    btn_set_parameter = tk.Button(window, text='Quick Start', width=35, height=1, command=quick_start)
    btn_set_parameter.place(x=20, y=600)


    window.mainloop()
