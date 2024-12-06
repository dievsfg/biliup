# @dievsfg  
from datetime import time
import os
import threading


class P_Config:
    douyu_cdns = [] # 创建类变量 列表 所有douyu的cdn 以元组的形式
    douyu_cdns_int = 0 # 创建类变量 当前使用的cdn的下标
    lock = threading.Lock()  # 创建一个锁对象
    reload_config_taskbool = False # 函数是否正在运行

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
        # 如果配置文件中没有内容 则报错
        if len(cls.douyu_cdns) == 0:
            raise ValueError('配置文件中没有内容!')
        
    # 定义一个函数当配置文件发生变化时 重新读取配置文件
    @classmethod
    async def reload_config(cls, config_file):
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
                
    # 定义一个函数来判断每个cdn是否可用  Todo：判断cdn是否可用
    @classmethod
    def check_cdn(cls, cdn):
        return True


    # 定义一个函数来获取douyu的cdn
    @classmethod
    def get_douyu_cdn_tuple(cls):
        with cls.lock:  # 使用上下文管理器自动获取锁
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
        return '%s/%s%s' % (cdn_tuple[0], rtmp_live, cdn_tuple[1])

