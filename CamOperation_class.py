# -- coding: utf-8 --
import sys
import threading
import msvcrt
import _tkinter
import tkinter.messagebox
from tkinter import *
from tkinter.messagebox import *
import tkinter as tk
import datetime
import inspect
import ctypes
import random
from PIL import Image, ImageTk
from ctypes import *
from tkinter import ttk

import datetime
# sys.path.append("./MvImport")
from MvImport.MvCameraControl_class import *

import Utils as U
import queue
import psutil


def Async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def Stop_thread(thread):
    Async_raise(thread.ident, SystemExit)


class CameraOperation():

    def __init__(self, obj_cam, st_device_list, n_connect_num=0, b_open_device=False, b_start_grabbing=False,
                 h_thread_handle=None, \
                 b_thread_closed=False, st_frame_info=None, b_exit=False, b_save_bmp=False, b_save_tif=False,
                 buf_save_image=None, \
                 n_save_image_size=0, frame_rate=0, exposure_time=0, gain=0):

        self.obj_cam = obj_cam
        self.st_device_list = st_device_list
        self.n_connect_num = n_connect_num
        self.b_open_device = b_open_device
        self.b_start_grabbing = b_start_grabbing
        self.b_thread_closed = b_thread_closed
        st_frame_info = st_frame_info
        self.b_exit = b_exit

        self.b_save_bmp = b_save_bmp
        self.b_save_tif = b_save_tif
        self.burst = False

        self.buf_save_image = buf_save_image
        self.h_thread_handle = h_thread_handle
        self.n_save_image_size = n_save_image_size
        self.frame_rate = frame_rate
        self.exposure_time = exposure_time
        self.gain = gain

        self.burst_num = 0
        self.IMGPATH = "C:/Users/jarrycyx/Desktop/HIK_IMG_DIR/"

        self.cache_queue = queue.Queue()

    def Open_device(self):
        if not self.b_open_device:
            # ch:选择设备并创建句柄 | en:Select device and create handle
            nConnectionNum = int(self.n_connect_num)
            stDeviceList = cast(self.st_device_list.pDeviceInfo[int(nConnectionNum)],
                                POINTER(MV_CC_DEVICE_INFO)).contents
            self.obj_cam = MvCamera()
            ret = self.obj_cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                self.obj_cam.MV_CC_DestroyHandle()
                return ret

            ret = self.obj_cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                self.b_open_device = False
                self.b_thread_closed = False
                return ret
            self.b_open_device = True
            self.b_thread_closed = False

            # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = self.obj_cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    ret = self.obj_cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
                    if ret != 0:
                        U.print_log("warning: set packet size fail! ret[0x%x]" % ret)
                else:
                    U.print_log("warning: set packet size fail! ret[0x%x]" % nPacketSize)

            stBool = c_bool(False)
            ret = self.obj_cam.MV_CC_GetBoolValue("AcquisitionFrameRateEnable", stBool)
            if ret != 0:
                U.print_log("get acquisition frame rate enable fail! ret[0x%x]" % ret)

            # ch:设置触发模式为off | en:Set trigger mode as off
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            if ret != 0:
                U.print_log("set trigger mode fail! ret[0x%x]" % ret)
            return 0

    def Start_grabbing(self, index, root, panel, lock):
        if False == self.b_start_grabbing and True == self.b_open_device:
            self.b_exit = False
            ret = self.obj_cam.MV_CC_StartGrabbing()
            if ret != 0:
                self.b_start_grabbing = False
                return ret
            self.b_start_grabbing = True
            try:
                self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread,
                                                        args=(self, index, root, panel, lock))
                self.h_thread_handle.start()
                self.b_thread_closed = True
            except:
                tkinter.messagebox.showerror('show error', 'error: unable to start thread')
                False == self.b_start_grabbing
            return ret

    def Stop_grabbing(self):
        if True == self.b_start_grabbing and self.b_open_device == True:
            # 退出线程
            ret = 0
            if self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_StopGrabbing()
            if ret != 0:
                self.b_start_grabbing = True
                self.b_exit = False
                return ret
            self.b_start_grabbing = False
            self.b_exit = True
            return ret

    def Close_device(self):
        if self.b_open_device:
            # 退出线程
            if self.b_thread_closed:
                self.b_thread_closed = False
                Stop_thread(self.h_thread_handle)
            ret = self.obj_cam.MV_CC_StopGrabbing()
            ret = self.obj_cam.MV_CC_CloseDevice()
            return ret

        # ch:销毁句柄 | Destroy handle
        self.obj_cam.MV_CC_DestroyHandle()
        self.b_open_device = False
        self.b_start_grabbing = False
        self.b_exit = True

    def Set_trigger_mode(self, strMode):
        if self.b_open_device:
            if "continuous" == strMode:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 0)
                return ret
            if "triggermode" == strMode:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 1)
                if ret != 0:
                    return ret
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource", 7)
                if ret != 0:
                    return ret
                return ret

    def Trigger_once(self, nCommand):
        if self.b_open_device:
            if 1 == nCommand:
                ret = self.obj_cam.MV_CC_SetCommandValue("TriggerSoftware")
                return ret

    def Get_parameter(self):
        if self.b_open_device:
            stFloatParam_FrameRate = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_FrameRate), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_exposureTime = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_exposureTime), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_gain = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_gain), 0, sizeof(MVCC_FLOATVALUE))
            ret = self.obj_cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatParam_FrameRate)
            self.frame_rate = stFloatParam_FrameRate.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("ExposureTime", stFloatParam_exposureTime)
            self.exposure_time = stFloatParam_exposureTime.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("Gain", stFloatParam_gain)
            self.gain = stFloatParam_gain.fCurValue
            return ret

    def Set_parameter(self, frameRate, exposureTime, gain):
        if '' == frameRate or '' == exposureTime or '' == gain:
            return -1
        if self.b_open_device:
            ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime", float(exposureTime))
            ret = self.obj_cam.MV_CC_SetFloatValue("Gain", float(gain))
            ret = self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(frameRate))
            return ret

    def Work_thread(self, index, root, panel, lock, printTimeLog=False, disp=True):
        stOutFrame = MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(stOutFrame))
        buf_cache = None
        numArray = None
        while True:
            if printTimeLog:
                U.print_log(self.burst_num, "Start")

            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 5000)
            if printTimeLog:
                U.print_log(self.burst_num, "Get img")

            if 0 == ret:
                #if None == buf_cache:
                buf_cache = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()

                st_frame_info = stOutFrame.stFrameInfo
                cdll.msvcrt.memcpy(byref(buf_cache), stOutFrame.pBufAddr, st_frame_info.nFrameLen)

                if printTimeLog:
                    U.print_log("Camera[%d]:get one frame: Width[%d], Height[%d], nFrameNum[%d]" % (
                        index, st_frame_info.nWidth, st_frame_info.nHeight, st_frame_info.nFrameNum))

                self.n_save_image_size = st_frame_info.nWidth * st_frame_info.nHeight * 3 + 2048

                if self.b_save_tif or self.b_save_bmp:
                    self.burst_num += 1
                    self.cache_queue.put((buf_cache, st_frame_info))

                    if st_frame_info.nFrameNum != self.burst_num - 1:
                        U.print_log("Missing {:d} frame".format(st_frame_info.nFrameNum - self.burst_num + 1))

                    if self.b_save_tif:
                        self.Save_Tif()  # ch:保存Jpg图片 | en:Save Jpg
                    if self.b_save_bmp:
                        self.Save_Bmp()  # ch:保存Bmp图片 | en:Save Bmp


                if (not self.b_save_bmp) and (not self.b_save_tif):
                    self.burst_num = 0

                if printTimeLog:
                    U.print_log(self.burst_num, "Save img")

            else:
                U.print_log("Camera[" + str(index) + "]:no data, ret = " + U.To_hex_str(ret))
                if self.b_exit:
                    break
                continue

            # 连拍时不显示图像
            if disp and (not self.burst):
                self.Disp_Img(buf_cache, st_frame_info, root, panel, lock, printTimeLog=printTimeLog)

            nRet = self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)

            if printTimeLog:
                U.print_log(self.burst_num, "Display rgb img")

            if self.b_exit:
                if img_buff is not None:
                    del img_buff
                break


    def Disp_Img(self, buf_cache, st_frame_info, root, panel, lock, printTimeLog=False):
        img_buff = None
        if img_buff is None:
            img_buff = (c_ubyte * self.n_save_image_size)()
        # 转换像素结构体赋值
        stConvertParam = MV_CC_PIXEL_CONVERT_PARAM()
        memset(byref(stConvertParam), 0, sizeof(stConvertParam))
        stConvertParam.nWidth = st_frame_info.nWidth
        stConvertParam.nHeight = st_frame_info.nHeight
        stConvertParam.pSrcData = cast(buf_cache, POINTER(c_ubyte))
        stConvertParam.nSrcDataLen = st_frame_info.nFrameLen
        stConvertParam.enSrcPixelType = st_frame_info.enPixelType

        # RGB直接显示
        if PixelType_Gvsp_RGB8_Packed == st_frame_info.enPixelType:
            numArray = U.Color_numpy(buf_cache, st_frame_info.nWidth,
                                     st_frame_info.nHeight)
        else:
            nConvertSize = st_frame_info.nWidth * st_frame_info.nHeight * 3
            stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
            stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
            stConvertParam.nDstBufferSize = nConvertSize
            ret = self.obj_cam.MV_CC_ConvertPixelType(stConvertParam)

            cdll.msvcrt.memcpy(byref(img_buff), stConvertParam.pDstBuffer, nConvertSize)
            numArray = U.Color_numpy(img_buff, st_frame_info.nWidth,
                                     st_frame_info.nHeight)

        if printTimeLog:
            U.print_log(self.burst_num, "Process rgb img")
        # 合并OpenCV到Tkinter界面中
        current_image = Image.fromarray(numArray).resize((500, 500), Image.ANTIALIAS)
        lock.acquire()  # 加锁
        imgtk = ImageTk.PhotoImage(image=current_image, master=root)
        panel.imgtk = imgtk
        panel.config(image=imgtk)
        root.obr = imgtk
        lock.release()  # 释放锁


    def Save_Bmp(self):  # sequence: save BMPs until b_save_bmp is set to False

        buf_cache, st_frame_info = self.cache_queue.get()
        if 0 == buf_cache:
            return

        time_stamp = st_frame_info.nHostTimeStamp
        self.buf_save_image = None
        file_path = self.IMGPATH + "IMG_" + str(st_frame_info.nFrameNum) \
                    + "_" + U.convert_time_stamp(time_stamp / 1000.0) + ".bmp"
        self.n_save_image_size = st_frame_info.nWidth * st_frame_info.nHeight * 3 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()

        stParam = MV_SAVE_IMAGE_PARAM_EX()
        stParam.enImageType = MV_Image_Bmp;  # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth = st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stParam.nHeight = st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stParam.nDataLen = st_frame_info.nFrameLen
        stParam.pData = cast(buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer = cast(byref(self.buf_save_image), POINTER(c_ubyte))
        stParam.nBufferSize = self.n_save_image_size  # ch:存储节点的大小 | en:Buffer node size

        return_code = self.obj_cam.MV_CC_SaveImageEx2(stParam)
        if return_code != 0:
            # tkinter.messagebox.showerror('show error', 'save bmp fail! ret = ' + U.To_hex_str(return_code))
            U.print_log('save bmp fail! ret = ' + U.To_hex_str(return_code))
        else:
            file_open = open(file_path.encode('ascii'), 'wb+')
            img_buff = (c_ubyte * stParam.nImageLen)()
            try:
                cdll.msvcrt.memcpy(byref(img_buff), stParam.pImageBuffer, stParam.nImageLen)
                file_open.write(img_buff)
                U.print_log("Seq. num", st_frame_info.nFrameNum, 'save bmp success!')
            except:
                raise Exception("get one frame failed:%s" % e.message)
            if None != img_buff:
                del img_buff
            if None != self.buf_save_image:
                del self.buf_save_image

            if not self.burst:
                self.b_save_bmp = False

    def Save_Tif(self):  # sequence: save BMPs until b_save_bmp is set to False

        buf_cache, st_frame_info = self.cache_queue.get()

        if 0 == buf_cache:
            return

        time_stamp = st_frame_info.nHostTimeStamp
        self.buf_save_image = None
        file_path = self.IMGPATH + "IMG_" + str(st_frame_info.nFrameNum) \
                    + "_" + U.convert_time_stamp(time_stamp / 1000.0) + ".tif"
        self.n_save_image_size = st_frame_info.nWidth * st_frame_info.nHeight * 3 * 2 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()

        stParam = MV_SAVE_IMG_TO_FILE_PARAM()
        stParam.enImageType = MV_Image_Tif  # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth = st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stParam.nHeight = st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stParam.nDataLen = st_frame_info.nFrameLen
        stParam.pData = cast(buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer = cast(byref(self.buf_save_image), POINTER(c_ubyte))
        stParam.nBufferSize = self.n_save_image_size  # ch:存储节点的大小 | en:Buffer node size
        stParam.pImagePath = bytes(file_path, encoding="utf8")

        return_code = self.obj_cam.MV_CC_SaveImageToFile(stParam)
        if return_code != 0:
            U.print_log('save TIF fail! ret = ' + U.To_hex_str(return_code))
            return

        if None != self.buf_save_image:
            del self.buf_save_image

        if not self.burst:
            self.b_save_tif = False

        U.print_log('save TIF success!')
