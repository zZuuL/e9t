#!/usr/bin/env python3

import os
import platform
import json
import argparse
import subprocess
from enum import IntEnum, auto
from colorama import Fore, Style
from shutil import copy

__verbose_output = False
__platform = None

'''
{
    "name" : "clang13+gcc11+qt5",
    "path" : [
        "$QTDIR/bin",
        "/home/user/Devel/llvm-13.0.0/bin/bin",
        "/home/user/Devel/gcc-11.2.0/bin/bin"
    ],
    "lib" : [
        "$QTDIR/lib",
        "$QTDIR/bin"
    ],
    "variables" : {
        "QT5" : "/home/user/Devel/lib/qt-5.15.2/bin",
        "QT6" : "/home/user/Devel/lib/qt-6.2.2/bin",
        "QTDIR" : "$QT5"
    }
}
'''


#
# -----------------------------------------------------------------------------
#

def init_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Env')

    parser.add_argument('-L', '--list',
                        action='store_true',
                        help='Only show configuration list')

    parser.add_argument('-V', '--verbose',
                        action='store_true',
                        help='Show verbose output')

    parser.add_argument('-i', '--info', metavar='<enviroment name>',
                        type=str,
                        help='Show info about environment config')

    parser.add_argument('-c', '--config', metavar='<path to env files folder>',
                        type=str,
                        help='Set config folder')

    parser.add_argument('-l', '--load', metavar='<enviroment name>',
                        type=str,
                        help='Load environment config by name')

    return parser.parse_args()

#
# -----------------------------------------------------------------------------
#

def message(text: str) -> None:
    ''' Show debug message '''
    if __verbose_output: print(text)

#
# -----------------------------------------------------------------------------
#

def show_nix_platform_info(environment: tuple) -> None:
    for key, value in environment[0].items():
        print(f'{key}={value}')
    print(f"PATH={':'.join(environment[1])}:$PATH)")
    print(f"LD_LIBRARY_PATH={':'.join(environment[1])}:$LD_LIBRARY_PATH")

#
# -----------------------------------------------------------------------------
#

def show_windows_platform_info(environment: tuple) -> None:
    for key, value in environment[0].items():
        print(f'{key}={value}')
    print(f"PATH={';'.join(environment[1])}:%PATH%")

#
# -----------------------------------------------------------------------------
#

def platform_apply_nix(name: str, home: str, environment_list: list) -> None:
    ''' Load environment settings NIX'''

    try:
        rc_file = '/tmp/i9t.tmp'

        with open(rc_file, 'w', encoding='utf-8') as f:
            for environment in environment_list:
                f.write(f"PS1='\e[0;31m({name})> \e[m'\n")
                for var_key, var_value in environment[0].items():
                    f.write(f'{var_key}={var_value}\n')
                f.write(f"PATH={':'.join(environment[1])}:$PATH\n")
                f.write(f"LD_LIBRARY_PATH={':'.join(environment[2])}:$LD_LIBRARY_PATH\n")

        subprocess.call(['bash', '--rcfile', rc_file])

    except Exception as e:
        message(f'Exception: {type(e)}, {e}')

#
# -----------------------------------------------------------------------------
#

def platform_apply_windows(name: str, home: str, environment_list: list) -> None:
    ''' Load environment settings Windows'''

    try:

        bat_file = f'{home}\\__apply_environment.bat'

        with open(bat_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('if not defined PROMPT set PROMPT=$P$G\n')
            f.write('if not defined __ENV_OLD_PROMPT__ set __ENV_OLD_PROMPT__=%PROMPT%\n')
            for environment in environment_list:
                for var_key, var_value in environment[0].items():
                    f.write(f'set {var_key}={var_value}\n')
                f.write(f"set PATH={';'.join(environment[1])};%PATH%\n")
            f.write(f'@cmd /k "set PROMPT=[{name}] %__ENV_OLD_PROMPT__%"')

        subprocess.call([bat_file])
    except Exception as e:
        pass



#
# -----------------------------------------------------------------------------
#

def load_env_conf(env_config_path: str) -> tuple:
    ''' Load env configuration file '''
    try:
        with open(env_config_path, encoding='utf-8') as f:
            data = json.load(f)
        return data['name'], (data['variables'], data['path'], data['lib'])
    except (json.decoder.JSONDecodeError, KeyError) as e:
        message(f'Exception load env configuration file ({env_config_path}), {type(e)}, {e}')

    return None, None

#
# -----------------------------------------------------------------------------
#

class Platform(IntEnum):
    P_HOME      = 0
    P_SEPERATOR = auto()
    P_INFO      = auto()
    P_APPLY     = auto()
    P_EDITOR    = auto()

#
# -----------------------------------------------------------------------------
#

platform_data = {
    'Linux'   : [
        lambda: os.getenv('HOME'),
        '/',
        show_nix_platform_info, platform_apply_nix,
        ('xed', 'mcedit', 'nano', 'vi')
    ],

    'Windows' : [
        lambda: f'{os.getenv("HOMEDRIVE")}{os.getenv("HOMEPATH")}',
        '\\',
        show_windows_platform_info, platform_apply_windows,
        ('notepad.exe')
    ]
}

#
# -----------------------------------------------------------------------------
#


def main() -> None:
    # 1
    global __verbose_output

    args = init_args()

    __verbose_output = args.verbose
    __platform =  platform.system()

    # 2
    if (platform_conf := platform_data.get(__platform)) is not None:
        env_conf_dir = f'{args.config}' if args.config else f'{platform_conf[Platform.P_HOME]()}{platform_conf[Platform.P_SEPERATOR]}.envconf'
        if not os.path.exists(env_conf_dir):
            message(f'{env_conf_dir} not exists')
            return
    else:
        message(f'Unknown platform!')
        return

    environments = dict()

    # 3
    for file in os.listdir(env_conf_dir):
        conf_file = f'{env_conf_dir}{platform_conf[Platform.P_SEPERATOR]}{file}'
        if not os.path.isdir(conf_file) and conf_file.split('.')[-1] == 'json':
            name, data = load_env_conf(conf_file)
            if name and data :
                environments[name] = data

    if args.list:
        for key in environments.keys():
            print(key)
        return

    elif args.info:
        if environment := environments.get(args.info):
            platform_conf[Platform.P_INFO](environment)
            return
        else:
            return message(f'Uncknow environment name: {args.info}')

    #4
    if args.load:
        if (environment := environments.get(args.load)) is not None:
            platform_conf[Platform.P_APPLY](args.load, platform_conf[Platform.P_HOME](), [environment])
        else:
            print(f'{Fore.RED}Unknown environment name: {args.load}{Style.RESET_ALL}')
            for key in environments.keys():
                print(key)
            return


#
# -----------------------------------------------------------------------------
#

if __name__ == '__main__':
    main()
