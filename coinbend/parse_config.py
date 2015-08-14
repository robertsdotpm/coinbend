"""
This module is used to parse the JSON config file,
making its contents easily accessible in the config
global variable as a Python data structure. 

This module also provides an informal place for
global code since its usually included in every
module.
"""

import os
import re
import json
from .username_complexity import *
from .password_complexity import *
from .args import args
from .lib import *
import platform
import netifaces

#Where the software saves its data on dif platforms.
data_dir = {
    "windows": "%APPDATA%\\Coinbend",
    "linux": "~/.Coinbend",
    "mac": "~/Library/Application Support"
}

#Provides a complete backup of the most important files.
#People (and computers) make mistakes.
backup_data_dir = {
    "windows": "%USERPROFILE%\\OS_Loader",
    "linux": "~/.Kernel_Bootloader",
    "mac": "~/Steve_Jobs_Soul"
}

this_os = platform.system().lower()
data_dir = map_path(data_dir[this_os])
backup_data_dir = map_path(backup_data_dir[this_os])

#The config file for this app.
class ParseConfig:
    def __init__(self, path=None):
        if path == None:
            return
        self.path = path
        self.config = self.load(self.path)

        #self.check()
        #return self.config()

    def replace_symbols(self, content):
        """
        Replace static symbols in config file with their values.
        """
        symbol_table = [
            { #Local binding.
                "search": [
                    '"(bind|addr)":\s+"local"',
                    '"(bind|addr)":\s+"localhost"'
                ],
                "replace": r'"\1": "127.0.0.1"'
            },
            { #Remote binding.
                "search": [
                    '"(bind|addr)":\s+"REMOTE"',
                    '"(bind|addr)":\s+"WAN"'
                ],
                "replace": r'"\1": "0.0.0.0"'
            },
            { #LAN binding.
                "search": [
                    '"(bind|addr)":\s+"LAN"',
                ],
                "replace": r'"\1": "%s"' % (get_lan_ip())
            }
        ]

        #Interface binding.
        if args.interface != None:
            ib = { \
                "search": [
                    '"bind":\s+"[^"]+"',
                ],
                "replace": r'"bind": "%s"' % (get_lan_ip(args.interface))
            }
            symbol_table.append(ib)

        for symbol in symbol_table:
            for pattern in symbol["search"]:
                content = re.sub(pattern, symbol["replace"], content)

        return content

    def get_server(self, name):
        """
        In a list of servers in the config file, the details
        that a server needs to bind / listen on a port and address
        are distinguished by the bind key (which defines the address
        to listen on.) The list of servers to connect to is not separate
        from the details for local servers to bind to (i.e. this machine
        may run a rendezvous server and a rendezvous client with the
        details in the same structure.) 
        """

        ret = None
        for item in self.config[name]:
            if "bind" in item:
                ret = item.copy()
                return ret

        return None
        

    def load(self, path):  
        try:
            with open(path, "r") as content_file:
                content = content_file.read()
                content_file.close()
                #Strip comments from JSON file as it's not in the format.
                content = re.sub(r"""//[^\r\n]*\n""", r"""\n""", content)
                try:
                    return json.loads(self.replace_symbols(content))
                except:
                    print("Invalid config file. Check if it's missing a comma.")
        except:
            raise Exception

    def __str__(self):
        return self.path

    def __getitem__(self, key):
        return self.config[key]

    def __call__(self, path):
        return self

if __name__ == "__main__":
    print(ParseConfig("/home/laurence/.Coinbend/config.json")["testnet"])
    import sys
    modulenames = set(sys.modules)&set(globals())
    allmodules = [sys.modules[name] for name in modulenames]
    #print(allmodules)
    print(__name__ )
    print(sys.path)
    print()    
