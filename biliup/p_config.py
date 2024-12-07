# @dievsfg  
import time
import os
import threading

import requests


class P_Config:
    douyu_cdns = [] # 创建类变量 列表 所有douyu的cdn 以元组的形式
    all_douyu_cdns = [] # 创建类变量 列表 所有douyu的cdn
    douyu_cdns_int = 0 # 创建类变量 当前使用的cdn的下标
    lock = threading.Lock()  # 创建一个锁对象
    reload_config_taskbool = False # 函数是否正在运行
    check_cdns_taskbool = False # 函数是否正在运行
    gotify_token = 'AH2ODO-1DINDTFO'
    gotify_url = 'http://01.diev.bid:20118'

    # 定义一个函数来读取配置文件并将其加入douyu_cdns
    @classmethod
    def read_config(cls, config_file):
        # 只有在第一次调用时或者配置文件发生变化才初始化
        if len(cls.douyu_cdns) > 0:
            return
        with open(config_file, 'r', encoding='utf-8') as file:
            for line in file:
                if not line.startswith('#') and line.strip() and len(line.strip().split()) == 2: # 如果不是注释且不是空行且只有一个空格
                    # 以空格分隔字符串 以元组的形式加入类变量douyu_cdns中
                    cls.douyu_cdns.append(tuple(line.strip().split()))
                    # 如果all_douyu_cdns中不存在该元组 则加入
                    if tuple(line.strip().split()) not in cls.all_douyu_cdns:
                        cls.all_douyu_cdns.append(tuple(line.strip().split()))
        # 后台调用检测函数
        t = threading.Thread(target=cls.check_cdns)
        t.start()
        
    # 定义一个函数当配置文件发生变化时 重新读取配置文件
    @classmethod
    def reload_config(cls, config_file):
        # 只有在第一次调用时才初始化
        if cls.reload_config_taskbool:
            return
        else:
            cls.reload_config_taskbool = True
            with cls.lock:
                cls.read_config(config_file)
        #判断配置文件内容是否发生变化 如果发生变化 则重新读取配置文件
        last_modified = os.path.getmtime(config_file)  # 更新最后修改时间 # 上一次配置文件的修改时间
        while True:
            current_modified = os.path.getmtime(config_file)  # 当前配置文件的修改时间
            if current_modified != last_modified:  # 如果当前配置文件的修改时间不等于上一次配置文件的修改时间
                last_modified = current_modified  # 更新最后修改时间
                with cls.lock:  # 使用上下文管理器自动获取锁
                    cls.douyu_cdns = []
                    cls.douyu_cdns_int = 0
                    cls.read_config(config_file)  # 重新读取配置文件
            time.sleep(10)  # 每10秒检查一次


    # 定义一个函数来获取douyu的cdn
    @classmethod
    def get_douyu_cdn_tuple(cls):
        with cls.lock:  # 使用上下文管理器自动获取锁
            # cls.douyu_cdns的长度为0 则返回空元组
            if len(cls.douyu_cdns) == 0:
                return ()
            # 如果douyu_cdns_int超出范围 则重置为0
            if cls.douyu_cdns_int >= len(cls.douyu_cdns):
                cls.douyu_cdns_int = 1
                return cls.douyu_cdns[cls.douyu_cdns_int - 1]
            cls.douyu_cdns_int += 1
            return cls.douyu_cdns[cls.douyu_cdns_int - 1]

    # 定义一个函数来获取douyu的cdn的url 传入url中间值 返回完整的url
    @classmethod
    def get_douyu_cdn_url(cls, rtmp_live):
        cdn_tuple = cls.get_douyu_cdn_tuple()
        if len(cdn_tuple) == 0:
            cls.send_gotify_message('斗鱼没有可用cdn', '可用cdn:0')
            return ""
        url = f'{cdn_tuple[0]}/live/{rtmp_live}{cdn_tuple[1]}'
        if cls.check_cdn_tuple(url):
            return url
        else:
            #在douyu_cdns删除不可用的cdn
            if cdn_tuple in cls.douyu_cdns:
                cls.douyu_cdns.remove(cdn_tuple)
                cls.douyu_cdns_int -= 1
            return cls.get_douyu_cdn_url(rtmp_live)

        # 定义一个函数来判断cdn是否可用 返回bool值
    @classmethod
    def check_cdn_tuple(cls, url):
        try:
            response = requests.get(url, stream=True, timeout=2)
            # 检查状态码
            if response.status_code == 200:
                #print("cdn可用1")
                return True

        except requests.RequestException as e:
            print(f"Error occurred while requesting the URL: {e}")
    
        return False

    # 定义一个函数 每小时检测cdns的可用性
    @classmethod
    def check_cdns(cls):
        # 只有在第一次调用时运行
        if cls.check_cdns_taskbool:
            return
        else:
            cls.check_cdns_taskbool = True
        while True:
            # 创建不可用cdns变量
            useful_cdns = []
            unuseful_cdns = []
            douyu_cdns = cls.all_douyu_cdns
            for cdn in douyu_cdns:
                if cls.check_cdn(cdn):
                    useful_cdns.append(cdn)
                else:
                    unuseful_cdns.append(cdn)
            if len(useful_cdns) > 0 and len(unuseful_cdns) > 0:
                with cls.lock:
                    # 从douyu_cdns中删除不可用的cdn
                    for cdn in unuseful_cdns:
                        # 如果douyu_cdns中存在该cdn 则删除
                        if cdn in cls.douyu_cdns:
                            cls.douyu_cdns.remove(cdn)
                    # 从douyu_cdns中加入可用的cdn
                    for cdn in useful_cdns:
                        # 如果douyu_cdns中不存在该cdn 则加入
                        if cdn not in cls.douyu_cdns:
                            cls.douyu_cdns.append(cdn)
            # 如果可用的cdn小于5 发送gotify消息
            if len(useful_cdns) < 5:
                cls.send_gotify_message('斗鱼可用cdn小于5', f'可用cdn:{len(useful_cdns)}\n{useful_cdns}')
            time.sleep(3600)

    # 定义一个函数来判断cdn是否可用 返回bool值
    @classmethod
    def check_cdn(cls, cdn):
        rtmp_live = '11156919rPcQDHpa.flv?wsAuth=7d58a797c57b62a13f74f517bbd72a4e&token=web-h5-85634402-11156919-7d8387b3fa5b87e87a14876a599d2a0435d5ed099b72b9a1&logo=0&expire=0&did=321da918cec5034b1c9246fa00051701&ver=Douyu_224120605&pt=2&st=3&sid=404748496&mcid2=0&origin=tct&mix=0&isp='
        url = f'{cdn[0]}/live/{rtmp_live}{cdn[1]}'
        print('\n'+url[:50])
        try:
            response = requests.get(url, stream=True, timeout=1)
            # 检查状态码
            if response.status_code == 200:
                print("cdn可用1")
                return True
        
            # 检查Server字段
            server_header = response.headers.get('Server', '')
            if 'dy_stream_media' in server_header:
                print("cdn可用2")
                return True
        
        except requests.exceptions.Timeout:
            print("请求超时，CDN可用3")
            return True
        except requests.exceptions.RequestException as e:
            print(f"发生错误: {e}")
    
        return False

    
    # 定义一个函数来发送gotify消息
    @classmethod
    def send_gotify_message(cls, title, message, priority=5):
        url3 = f"{cls.gotify_url}/message?token={cls.gotify_token}"
        data = {
            'message': message,
            'priority': str(priority),
            'title': title
        }
    
        try:
            response = requests.post(url3, data=data)
            response.raise_for_status()  # 如果响应状态码不是200，会抛出异常
        except requests.RequestException as e:
            error_info = f"Post request error: {e}"
            print(error_info)
            return
    
        return 


P_Config.reload_config("./douyucdns.txt")


