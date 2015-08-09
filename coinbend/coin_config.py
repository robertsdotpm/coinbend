"""
Read and patch config files for different cryptocurrencies.
"""
import re
import os
import sys
from .json_rpc import *
from .password_complexity import *
from .username_complexity import *
from .currency_type import *
from .lib import *
import socket
import random

class CoinConfig():
    def __init__(self, file_path, coin, testnet):
        self.coin = coin
        self.file_path = file_path
        self.testnet = testnet
        self.conf = None
        self.load()
        self.updated = self.patch()
        if self.updated:
            self.save_changes()

    def load(self):
        #Todo: Backup old conf file.
        if not os.path.exists(self.file_path):
            return

        content = ""
        try:
            with open(self.file_path, "r") as fp:
                self.conf = []
                for line in fp.readlines():
                    #Valid lines only.
                    line = line.strip()
                    if "#" in line:
                        continue
                    if "=" not in line:
                        continue
                    p = r"""([a-zA-Z0-9]+)=([\s\S]+)"""
                    pieces = re.match(p, line)
                    if pieces == None:
                        continue

                    #Store conf line.
                    lookup = {}
                    lookup[pieces.group(1)] = pieces.group(2)
                    self.conf.append(lookup)
        except:
            return
        
    def set_field(self, name, value, old_value=None):
        #Config not loaded.
        if self.conf == None:
            return

        #Set field.
        name = str(name)
        value = str(value)
        is_set = 0
        for lookup in self.conf:
            if name == list(lookup)[0]:
                if old_value != None:
                    if lookup[name] == old_value:
                        lookup[name] = value
                        is_set = 1
                else:
                    lookup[name] = value
                    is_set = 1

        #Add new field.
        if not is_set:
            lookup = {}
            lookup[name] = value
            self.conf.append(lookup)
            is_set = 1

    def get_field(self, name):
        #Config not loaded.
        if self.conf == None:
            return None

        #Find value.
        for lookup in self.conf:
            if name == list(lookup)[0]:
                return lookup[name]

        #Not found.
        return None

    #Patch conf file for working with exchange.
    def patch(self):
        if self.conf != None:
            old_conf = self.conf[:]
        else:
            old_conf = None

        """
        Set testnet or mainnet mode on coin client based
        on the mode in the config.
        """
        self.set_field("testnet", self.testnet)

        """
        Disable SSL for simplicity. This isn't a security
        risk because the RPC interface will be reconfigured
        for localhost later on.
        """
        self.set_field("rpcssl", "0")

        """
        Disable outside connectivity to the RPC instance.
        This just sets the allow only to localhost.
        """
        self.set_field("rpcallowip", "127.0.0.1")

        """
        Disable mining to avoid the CPU from being raped.
        This is to avoid performance issues.
        """
        self.set_field("gen", "0")

        """
        Tell the coin client to accept RPC calls.
        """
        self.set_field("server", "1")

        """
        Set the RPC user.
        """
        requirements = ["uppercase", "lowercase", "numeric"]
        pc = PasswordComplexity(requirements, 15)
        uc = UsernameComplexity()
        rcp_user = self.get_field("rpcuser")
        if rcp_user != None:
            if not uc.is_valid(rcp_user):
                self.set_field("rpcuser", pc.generate_password())
        else:
            self.set_field("rpcuser", pc.generate_password())

        """
        Set the RPC password.
        """
        pc = PasswordComplexity(requirements, 40)
        rpc_pass = self.get_field("rpcpassword")
        if rpc_pass != None:
            if not pc.is_valid(rpc_pass):
                self.set_field("rpcpassword", pc.generate_password())
        else:
            self.set_field("rpcpassword", pc.generate_password())

        """
        Generate random port and compare against taken ports
        and ports of all the coin clients already loaded.
        Set the RPC port.

        Note: There's a chance the new port conflicts
        with an existing client configuration. This is taken
        care of in the load_coins function.
        """
        if self.get_field("rpcport") == None:
            max_port = 65535
            while 1:
                rand_port = random.randrange(1, max_port)
                for coin in list(coins):
                    #This is us.
                    if coin == self.coin:
                        break

                    #Port conflict with previous coin client.
                    if coins[coin]["coin_config"].get_field("rpcport") == rand_port:
                        continue

                    #Port already in use.
                    try:
                        socket.create_connection(("127.0.0.1", rand_port), 1)
                        continue
                    except:
                        pass
                break
            self.set_field("rpcport", rand_port)

        updated = 0
        print(self.conf)
        print(old_conf)
        if self.conf != old_conf and self.conf != None:
            updated = 1
        return updated
    
    def save_changes(self):
        if self.updated:
            print("Updating " + str(self.coin))
            try:
                #Convert to conf format.
                content = ""
                for field in self.conf:
                    name = list(field)[0]
                    value = field[name]
                    content += "%s=%s\n\n" % (name, value)

                #Save changes.
                with open(self.file_path, "w") as fp:
                    fp.write(content)

                #Success.
                return 1
            except Exception as e:
                print(e)
                return 0
        return 0

def load_coins(this_os, testnet, coin_names=[]):
    #Find coin names in common datadirs.
    global coins
    coins = {}
    coin_search_path = {
        "windows": map_path("%APPDATA%"),
        "linux": map_path("~"),
        "mac": map_path("~/Library/Application Support")
    }
    dirs = os.listdir(coin_search_path[this_os])
    p = r"""^[.]?([a-zA-Z0-9]+?coin)$"""
    coin_matches = []
    for directory in dirs:
        coin = re.match(p, directory)
        if coin != None:
            coin_matches.append(coin.group(1).lower())

    #Append manual coin names to matches.
    coin_matches = coin_matches + coin_names

    #Load config files.
    ports = []
    conf_paths = []
    for coin in coin_matches:
        #Load config.
        conf_filename = coin + ".conf"
        if this_os == "linux":
            conf_dir = "." + coin
        if this_os == "windows" or this_os == "mac":
            conf_dir = coin.capitalize()
        conf_path = os.path.join(coin_search_path[this_os], conf_dir, conf_filename)
        conf_paths.append(conf_path)
        coin_config = CoinConfig(conf_path, coin, testnet)

        #Coin not loaded: skip.
        if coin_config.conf == None:
            print("Unable to load " + str(coin_config.coin))
            print("Maybe there was a permission error writing to the config file? Please check the coin's config file is writable.")
            print()
            input("Press enter to continue.")
            continue

        #Try connect RPC.
        connected = 0
        rpc_user = coin_config.get_field("rpcuser")
        rpc_pass = coin_config.get_field("rpcpassword")
        rpc_addr = "127.0.0.1"
        rpc_port = coin_config.get_field("rpcport")
        endpoint = "http://%s:%s@%s:%s" % (rpc_user, rpc_pass, rpc_addr, rpc_port)
        rpc = None

        coins[coin] = {
            "coin_config": coin_config,
            "conf_path": conf_path,
            "rpc": {
                "sock": rpc,
                "endpoint": endpoint,
                "addr": rpc_addr,
                "port": rpc_port,
                "user": rpc_user,
                "pass": rpc_pass,
            },
            "connected": connected,
            "balance": C("0"),
            "precision": 8,
            "address": "",
            "tx_fee": C("0"),
            "dust_threshold": C("0"),
            "testnet": 1,
            "updated": 0
        }
        ports.append(rpc_port)

    #Retry until there's no port conflicts.
    if len(list(set(ports))) != len(ports):
        #Delete old configs and clear state.
        for conf_path in conf_paths:
            os.remove(conf_path)
        coins = {}

        """
        Recursively calls itself forever until
        there are no conflicts. Ugly brute force,
        but should work.
        """
        load_coins()
        return

    updated = 0
    for coin in list(coins):
        #Attempt to connect RPC instances.
        try:
            #Causes an exception if not connected.
            rpc = coins[coin]["rpc"]["sock"] = JsonRpc(coins[coin]["rpc"]["endpoint"])
            get_info = rpc.getinfo()
            balance = coins[coin]["balance"] = C(get_info["balance"])
            coins[coin]["precision"] = balance.decimal_len()
            coins[coin]["address"] = rpc.getaccountaddress("0")
            coins[coin]["connected"] = 1
            coins[coin]["testnet"] = get_info["testnet"]
            if coins[coin]["coin_config"].updated:
                updated = coins[coin]["updated"] = 1

            #Calculate and set TX fee.
            tx_fee = C(get_info["paytxfee"])
            relay_fee = C(0)
            if "relayfee" in get_info:
                relay_fee = C(get_info["relayfee"])
            if "minrelaytxfee " in get_info:
                relay_fee = C(get_info["minrelaytxfee "])
            if relay_fee > tx_fee:
                tx_fee = relay_fee
            if tx_fee == C(0):
                tx_fee = C("0.001")
            coins[coin]["tx_fee"] = tx_fee

            """
            Set the dust_threshold -- this is the smallest value that an output can be for a coin before the coin either rejects it or imposes another tx_fee as a penalty. In the future there will need to be better code to determine this but its hard to do cross-currency.

            There seems to be a small relationship between the dust threshold having around a 0.5 cent economic value but if the dust_threshold is calculated based on exchange rate huge swings for new currencies would make the code highly unstable.
            """
            coins[coin]["dust_threshold"] = tx_fee

            """
            Unfortunately, even if a coin supports more than 16 decimal places our database can't store it. Got to draw the limit somewhere.
            """
            max_precision = C(0).precision
            if coins[coin]["precision"] > max_precision:
                coins[coin]["precision"] = max_precision
        except Exception as e:
            print(e)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            coins[coin]["rpc"]["sock"] = None
            coins[coin]["connected"] = 0

    if updated:
        print("One or more of your coins have had their config files updated so Coinbend can connect. Please restart your coin clients and then restart the Coinbend client.")
        print()
        input("Press enter to exit ...")
        exit()

    return coins

if __name__ == "__main__":
    pass

