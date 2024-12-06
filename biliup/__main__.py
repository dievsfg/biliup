#!/usr/bin/python3
# coding:utf8
import argparse
import asyncio
import logging.config
import platform
import shutil

from biliup.p_config import P_Config # @dievsfg
from pathlib import Path # @dievsfg

import biliup.common.reload
from biliup.config import config
from biliup import __version__, LOG_CONF
from biliup.common.Daemon import Daemon
from biliup.common.reload import AutoReload
from biliup.common.log import DebugLevelFilter


def arg_parser():
    daemon = Daemon('watch_process.pid', lambda: main(args))
    parser = argparse.ArgumentParser(description='Stream download and upload, not only for bilibili.')
    parser.add_argument('--version', action='version', version=f"v{__version__}")
    parser.add_argument('-H', help='web api host [default: 0.0.0.0]', dest='host')
    parser.add_argument('-P', help='web api port [default: 19159]', default=19159, dest='port')
    parser.add_argument('--no-http', action='store_true', help='disable web api')
    parser.add_argument('--static-dir', help='web static files directory for custom ui')
    parser.add_argument('--password', help='web ui password ,default username is biliup', dest='password')
    parser.add_argument('-v', '--verbose', action="store_const", const=logging.DEBUG, help="Increase output verbosity")
    parser.add_argument('--config', type=argparse.FileType(mode='rb'),
                        help='Location of the configuration file (default "./config.yaml")')
    parser.add_argument('--no-access-log', action='store_true', help='disable web access log')
    subparsers = parser.add_subparsers(help='Windows does not support this sub-command.')
    # create the parser for the "start" command
    parser_start = subparsers.add_parser('start', help='Run as a daemon process.')
    parser_start.set_defaults(func=daemon.start)
    parser_stop = subparsers.add_parser('stop', help='Stop daemon according to "watch_process.pid".')
    parser_stop.set_defaults(func=daemon.stop)
    parser_restart = subparsers.add_parser('restart')
    parser_restart.set_defaults(func=daemon.restart)
    parser.set_defaults(func=lambda: asyncio.run(main(args)))
    args = parser.parse_args()
    biliup.common.reload.program_args = args.__dict__

    is_stop = args.func == daemon.stop

    if not is_stop:
        from biliup.database.db import SessionLocal, init
        with SessionLocal() as db:
            from_config = False
            try:
                config.load(args.config)
                from_config = True
            except FileNotFoundError:
                print(f'新版本不依赖配置文件，请访问 WebUI 修改配置')
            if init(args.no_http, from_config):
                if from_config:
                    config.save_to_db(db)
            config.load_from_db(db)
        # db.remove()
        LOG_CONF.update(config.get('LOGGING', {}))
        if args.verbose:
            LOG_CONF['loggers']['biliup']['level'] = args.verbose
            LOG_CONF['root']['level'] = args.verbose
        logging.config.dictConfig(LOG_CONF)
        logging.getLogger('httpx').addFilter(DebugLevelFilter())
        # logging.getLogger('hpack').setLevel(logging.CRITICAL)
        # logging.getLogger('httpx').setLevel(logging.CRITICAL)
    if platform.system() == 'Windows':
        if is_stop:
            return
        return asyncio.run(main(args))
    args.func()


async def main(args):
    from biliup.app import event_manager

    event_manager.start()

    # 启动时删除临时文件夹
    shutil.rmtree('./cache/temp', ignore_errors=True)

    interval = config.get('check_sourcecode', 15)

    if not args.no_http:
        import biliup.web
        runner = await biliup.web.service(args)
        detector = AutoReload(event_manager, runner.cleanup, interval=interval)
        biliup.common.reload.global_reloader = detector
        await detector.astart()
    else:
        import biliup.common.reload
        detector = AutoReload(event_manager, interval=interval)
        biliup.common.reload.global_reloader = detector
        await asyncio.gather(detector.astart())


class GracefulExit(SystemExit):
    code = 1


# @dievsfg
def run_async_function(async_func, *args, **kwargs):
    loop = asyncio.new_event_loop()  # 创建一个新的事件循环
    asyncio.set_event_loop(loop)  # 设置新的事件循环
    loop.run_in_executor(None, async_func, *args, **kwargs)  # 在后台线程中运行异步函数

if __name__ == '__main__':
    # 后台初始化自定义douyucdns  @dievsfg
    # 获取文件路径 文件在当前目录的data/douyucdns.txt
    file_path_douyucdns = Path.cwd().joinpath("data/douyucdns.txt")
    print("文件路径：", file_path_douyucdns)
    try:
        with open('output.txt', 'w') as file:
            file.write('文件路径：' + str(file_path_douyucdns) + '\n')
            #文件存在检测
            if file_path_douyucdns.exists():
                file.write('文件存在\n')
            else:
                file.write('文件不存在\n')
    except Exception as e:
        print(f'An error occurred: {e}')
    # 创建并启动异步任务，但不需要等待它完成 @dievsfg
    # 创建并启动线程来运行异步函数 @dievsfg
    run_async_function(P_Config.reload_config, file_path_douyucdns)
    #P_Config.reload_config(file_path_douyucdns)

    arg_parser()
