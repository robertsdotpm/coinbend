"""
Events:
    * Arrival - Transaction was accepted to the mempool.
    * Confirm - Minimum confirmations reached for a transaction.
    * Mutate - Same as confirm but called if transaction was mutated.
    * Fraud - Same as confirm but called if transaction was double spent.
"""

import time
import binascii
import hashlib
import re

from bitcoin import SelectParams
from bitcoin.core import b2x, b2lx, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret, CKey
from .bitcoinrpc.authproxy import JSONRPCException

from .globals import *
from .coinlib import *
from .database import *
from .currency_type import *
from .lib import *

class TXMonitor():
    def __init__(self, coins, confirmations=6, heights=None, debug=0):
        self.address_types = ["p2pkh", "p2sh"]
        self.confirmations = confirmations
        self.coins = coins
        self.latest_blocks = {} # currency > block.
        self.processed_blocks = {}
        self.get_latest_blocks(heights)
        self.watching = {}
        self.watches_by_id = {}
        self.inputs = {}
        self.blocks = {}
        self.addresses = {}
        for currency in coins:
            self.watching[currency] = {} #watch_id > watch.
            self.inputs[currency] = {} #Txid > input.
            self.blocks[currency] = {} #Block hash > block.
            self.processed_blocks[currency] = None #Block hash.
            try:
                self.addresses[currency] = Address(currency=currency, coins=self.coins)
            except:
                continue

        #Limit to how many blocks can be checked successively to stop infinite loops when the chain is out of date or behind.
        self.max_block_checks = 1000
        self.last_run_time = time.time()
        self.debug = debug
        if self.debug:
            self.check_interval = None
        else:
            self.check_interval = 30 * 1
        self.first_run = 1

    def get_heights(self):
        heights = {}
        for currency in self.latest_blocks:
            heights[currency] = self.latest_blocks[currency]["height"]

        return heights

    def get_latest_blocks(self, heights):
        for currency in self.coins:
            rpc = self.coins[currency]["rpc"]["sock"]
            if rpc == None:
                continue

            if heights != None:
                if currency in heights:
                    height = heights[currency]
                else:
                    height = rpc.getblockcount()
            else:
                height = rpc.getblockcount()
            block_hash = rpc.getblockhash(height)
            block = rpc.getblock(block_hash)
            self.latest_blocks[currency] = block

    def check(self):
        global error_log_path

        try:
            elapsed = int(time.time() - self.last_run_time)
            if self.check_interval != None:
                if elapsed < self.check_interval:
                    return
            self.last_run_time = time.time()
            print("Checking TX monitor.")

            for currency in self.latest_blocks:
                rpc = self.coins[currency]["rpc"]["sock"]
                block = self.latest_blocks[currency]
                height = rpc.getblockcount()

                #Skip unconnected RPCs.
                if rpc == None:
                    print("Rpc sock is broken.")
                    continue

                #This should never ever happen.
                if self.latest_blocks[currency] == None and not self.first_run:
                    print("\a\a\a")
                    error = "Latest blocks was detected to be none!!!! Attempting to recover."
                    log_exception(error_log_path, error)
                    print(error)
                    self.get_latest_blocks(heights=None)

                #A new block might of arrived.
                if height > block["height"]:
                    block = rpc.getblock(block["hash"])

                    #This block has been orphaned.
                    #Step back until unfrozen.
                    if "nextblockhash" not in block:
                        orphaned = []
                        while int(block["confirmations"]) < 1 or "nextblockhash" not in block:
                            """
                            If there's an error between now and setting the new latest block subsequent code will reload the latest_blocks when it detects None.
                            """
                            self.latest_blocks[currency] = None

                            print("Found orphan block " + str(block["hash"]))
                            print("\a\a\a\a")

                            #Prevent us from ever getting stuck.
                            #(Might occur if pruning is enabled.)
                            height = block["height"]
                            while "previousblockhash" not in block:
                                print("Previous block hash not found~~~!!!!")
                                print("Found orphan block " + str(block["hash"]))
                                print("\a\a\a\a")
                                try:
                                    block_hash = rpc.getblockhash(height)
                                except:
                                    height -= 1
                                    continue
                                block = rpc.getblock(block_hash)
                                orphaned.append(block)
                                height -= 1
                            
                            #Go back until we have a valid block.
                            block_hash = block["previousblockhash"]
                            block = rpc.getblock(block_hash)
                            self.latest_blocks[currency] = block
                            orphaned.append(block)

                            #Check next block hash is valid.
                            if "nextblockhash" in block:
                                if re.match("^[a-fA-F0-9]+$", str(block["nextblockhash"])) == None:
                                    del block["nextblockhash"]

                        #Process orphans.
                        for orphan in orphaned:
                            #All the watches are decreased since its a chain.
                            for seen_block_hash in list(self.blocks[currency]):
                                seen_block = self.blocks[currency][seen_block_hash]
                                for watch_id in seen_block:
                                    watch = self.watching[currency][watch_id]
                                    if watch["confirmations"]:
                                        watch["confirmations"] -= 1
                                        if not watch["confirmations"]:
                                            watch["event"] = None
                                            self.remove_seen(currency, watch_id)

                                    print("Updated watch due to orphan.")
                                    print(watch)

                                #Delete old block container if needed.
                                if not len(seen_block):
                                    self.blocks[currency].pop(seen_block_hash, None)

                            #Clear processed blocks.
                            if self.processed_blocks[currency] == orphan["hash"]:
                                self.processed_blocks[currency] = None

                #Process blocks.
                loop = 1
                block_checks = 1
                while loop and block_checks <= self.max_block_checks:
                    print("")
                    print("Checking: " + str(currency) + " " + str(block["hash"]))

                    #Already processed, skip block.
                    if (self.processed_blocks[currency] == block["hash"] and self.processed_blocks[currency] != None) or block["hash"] in self.blocks[currency]:
                        if "nextblockhash" in block:
                            block = rpc.getblock(block["nextblockhash"])
                        else:
                            print("Skipping: already processed.")
                            loop = 0
                            break

                    #Processing block.
                    if self.debug:
                        print("Processing block: " + str(block["hash"]))

                    #Get transactions.
                    calls = []
                    for txid in block["tx"]:
                        calls.append(["getrawtransaction", txid])
                    if len(calls) and len(self.watching[currency]):
                        tx_hexs = rpc.batch(calls)
                    else:
                        tx_hexs = []

                    #Does this transaction apply to any watches?
                    old_watches = []
                    double_spends = []
                    for watch_id in list(self.watching[currency]):
                        #Already found TX in chain, increment confirmations.
                        watch = self.watching[currency][watch_id]
                        print(watch)
                        if watch["event"] != None:
                            watch["confirmations"] += 1
                        else:
                            #Check transactions against watch.
                            for tx_hex in tx_hexs:
                                event = None
                                tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))

                                #Confirm, no malleability or double-spend.
                                if watch["needle"]["type"] == "tx_hex":
                                    if tx_hex == watch["needle"]["value"]:
                                        event = "confirm"
                                    else:
                                        #Identical but mutated transaction.
                                        if compare_transactions(tx_hex, watch["needle"]["value"]):
                                            event = "mutate"
                                        else:
                                            #Double spend detected.
                                            inputs = {}
                                            for vin in tx.vin:
                                                input_txid = b2lx(vin.prevout.hash)
                                                input_index = vin.prevout.n
                                                if input_txid not in self.inputs[currency]:
                                                    continue

                                                if input_index in self.inputs[currency][input_txid]:
                                                    """
                                                    Record the suspected double spent inputs. Note that this could still apply to any of the other watches as either malleable or confirmed. We don't actually know until all the watches have been processed first.
                                                    """
                                                    if input_txid not in inputs:
                                                        inputs[input_txid] = []
                                                    inputs[input_txid].append(input_index)

                                            #Record double spends.
                                            if inputs != {}:
                                                double_spend = {
                                                    "tx_hex": tx_hex,
                                                    "inputs": inputs,
                                                    "watch_id": watch_id
                                                }
                                                double_spends.append(double_spend)

                                #Pay to pub key hash.
                                #Pay to script hash.
                                if watch["needle"]["type"] in self.address_types:
                                    ret = self.parse_address(tx, currency)
                                    if self.in_found_addresses(watch["needle"], ret):
                                        event = "confirm"
                                        watch["address"]["type"] = ret["type"]
                                        watch["address"]["value"] = ret["value"]

                                #Found something.
                                #Update confirmation count / status.
                                if event != None:
                                    watch["found_tx_hex"] = tx_hex
                                    watch["event"] = event
                                    watch["confirmations"] += 1

                                    #Save block this was found in.
                                    if block["hash"] not in self.blocks[currency]:
                                        self.blocks[currency][block["hash"]] = []
                                    self.blocks[currency][block["hash"]].append(watch_id)
                                    watch["block"] = block["hash"]
                                    watch["height"] = block["height"]

                                    #Watch is satisfied, no reason to continue.
                                    break

                        #Do callback if confirmation threshold met.
                        if watch["confirmations"] >= self.confirmations:
                            #Execute callback.
                            event = watch["event"]
                            code = watch["callback"][event]
                            needle = watch["needle"]
                            if code != None:
                                self.do_callback(watch, code, event, tx_hex, needle)

                            #Signal watch to be deleted.
                            old_watches.append(watch_id)

                    #Check for double spends.
                    for double_spend in double_spends:
                        found = 0
                        for watch_id in list(self.watching[currency]):
                            watch = self.watching[currency][watch_id]
                            if watch["found_tx_hex"] == double_spend["tx_hex"]:
                                found = 1

                        #This is an actual double spend.
                        if not found:
                            #Record event.
                            watch = self.watching[currency][double_spend["watch_id"]]
                            watch["found_tx_hex"] = double_spend["tx_hex"]
                            watch["event"] = "fraud"
                            watch["confirmations"] += 1

                            #Save block this was found in.
                            if block["hash"] not in self.blocks[currency]:
                                self.blocks[currency][block["hash"]] = []
                            self.blocks[currency][block["hash"]].append(watch_id)
                            watch["block"] = block["hash"]

                    #Remove old watches.
                    for old_watch_id in old_watches:
                        old_watch = self.watching[currency][old_watch_id]
                        if old_watch["needle"]["type"] != "tx_hex":
                            if not old_watch["expires"]:
                                continue

                        self.remove_watch(currency, old_watch_id)

                    #Record that this block has been processed.
                    self.processed_blocks[currency] = block["hash"]

                    #Get next block.
                    if "nextblockhash" in block:
                        block = rpc.getblock(block["nextblockhash"])
                    else:
                        #Made it to chain tip.
                        loop = 0
                        self.latest_blocks[currency] = block
                        break

                    block_checks += 1

                #Get transactions in mem pool.
                mempool_tx = rpc.getrawmempool()

                #Get transactions.
                calls = []
                for txid in mempool_tx:
                    calls.append(["getrawtransaction", txid])
                if len(calls) and len(self.watching[currency]):
                    tx_hexs = rpc.batch(calls)

                    #Does this mempool transaction apply to any watches?
                    for watch_id in list(self.watching[currency]):
                        watch = self.watching[currency][watch_id]

                        #Process tx_hex.
                        for tx_hex in tx_hexs:
                            #Confirm or no malleability.
                            found = 0
                            if watch["needle"]["type"] == "tx_hex":
                                if tx_hex == watch["needle"]["value"]:
                                    found = 1
                                else:
                                    #Identical but mutated transaction.
                                    if compare_transactions(tx_hex, watch["needle"]["value"]):
                                        found = 1

                            #Pay to pub key hash.
                            #Pay to script hash.
                            if watch["needle"]["type"] in self.address_types:
                                ret = self.parse_address(tx, currency)
                                if self.in_found_addresses(watch["needle"], ret):
                                    watch["address"]["type"] = ret["type"]
                                    watch["address"]["value"] = ret["value"]
                                    found = 1
                                    break

                            #Process callback.
                            if found:
                                event = "arrival"
                                if watch["callback"][event] != None:
                                    code = watch["callback"][event]
                                    needle = watch["needle"]
                                    self.do_callback(None, code, event, tx_hex, needle)
                                    watch["callback"][event] = None

                                    #Remove the watch if there's no other callbacks.
                                    other_callbacks = 0
                                    for callback_event in list(watch["callback"]):
                                        if watch["callback"][callback_event] != None:
                                            other_callbacks = 1

                                    if not other_callbacks:
                                        self.remove_watch(currency, watch_id)

                                break
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)

        self.first_run = 0

    def in_found_addresses(self, needle, found_addresses):
        for found_address in found_addresses:
            if found_address["type"] == needle["type"] and found_address["value"] == needle["value"]:
                return 1

        return 0

    def parse_address(self, tx, currency):
        #Supported address types.
        addresses = {
            "p2sh": [OP_HASH160, None, OP_EQUAL],
            "p2pkh": [OP_DUP, OP_HASH160, None, OP_EQUALVERIFY, OP_CHECKSIG]
        }

        #Check first output only for expected address.
        insert_main = 1
        found_addresses = []
        for address_type in ["p2sh", "p2pkh"]:
            expected_pub_key = addresses[address_type]
            for vout_index in range(0, len(tx.vout)):
                output = tx.vout[vout_index]
                found_pub_key = list(output.scriptPubKey)
                match_no = 0
                hash_index = 0

                #Count expected parts for this output.
                for i in range(0, len(found_pub_key)):
                    if i > len(expected_pub_key) - 1:
                        match_no = 0
                        break

                    if expected_pub_key[i] == None:
                        hash_index = i
                        match_no += 1
                        continue

                    if expected_pub_key[i] == found_pub_key[i]:
                        match_no += 1

                #All parts found -- addr found.
                if match_no == len(expected_pub_key):
                    addr_hash = found_pub_key[hash_index]
                    addr = self.addresses[currency].construct_address(addr_hash, hashed=1)
                    ret = {
                        "type": address_type,
                        "value": addr,
                        "vout": vout_index,
                        "script_pub_key": found_pub_key
                    }

                    """
                    The address for the first output is the most important to decide what the address is if there's multiple outputs for the same transaction that have an address type / valid address.
                    """
                    if insert_main:
                        found_addresses.insert(0, ret)
                        insert_main = 0
                    else:
                        found_addresses.append(ret)

        #Nothing found -- unknown.
        if not len(found_addresses):
            ret = [{
                "type": "unknown",
                "value": ""
            }]

            return ret
        else:
            return found_addresses

    def remove_inputs(self, currency, tx):
        #Remove inputs.
        for vin in tx.vin:
            input_txid = b2lx(vin.prevout.hash)
            input_index = vin.prevout.n
            if input_txid in self.inputs[currency]:
                self.inputs[currency][input_txid].remove(input_index)
                if not len(self.inputs[currency][input_txid]):
                    self.inputs[currency].pop(input_txid, None)
            else:
                continue

    def remove_seen(self, currency, watch_id):
        #Prune watch_id from blocks.
        watch = self.watching[currency][watch_id]
        in_block = watch["block"]
        if watch_id in self.blocks[currency][in_block]:
            self.blocks[currency][in_block].remove(watch_id)

        #Delete old block container if needed.
        if not len(self.blocks[currency][in_block]):
            self.blocks[currency].pop(in_block, None)

    def remove_watch(self, currency, watch_id):
        watch = self.watching[currency][watch_id]
        del self.watches_by_id[watch_id]
        if watch["needle"]["type"] == "tx_hex":
            self.remove_inputs(currency, watch["tx"])
        self.remove_seen(currency, watch_id)
        self.watching[currency].pop(watch_id, None)

    def find_watch(self, watch_id):
        if watch_id not in self.watches_by_id:
            return None
        else:
            return self.watches_by_id[watch_id]

    def find_watch_partial(self, watch_id_needle):
        ret = []
        for watch_id in list(self.watches_by_id):
            if watch_id_needle in watch_id:
                ret.append(self.watches_by_id[watch_id])

        return ret

    def do_callback(self, watch, code, event, tx_hex, needle):
        print("Doing callback.")
        print("\a\a\a")

        #Context to execute callback.
        def callback(event, tx_hex, needle):
            if callable(code):
                code(event, tx_hex, needle)
            else:
                exec(code, globals())

        #Execute callback.
        callback(event, tx_hex, needle)
        
        #Update DB.
        if watch != None:
            self.update_watch(watch["id"])

    def save_watch(self, watch_id):
        watch = self.watches_by_id[watch_id]
        timestamp = int(time.time())
        with Transaction() as tx:
            sql = "INSERT INTO `transactions` (`txid`, `found_tx_hex`, `needle_value`, `height`, `event`, `needle_type`, `watch_id`, `currency`, `tx_fees`, `created_at`, `address_type`, `address_value`, `memo`, `amount`, `expires`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            tx.execute(sql, (watch["txid"], watch["found_tx_hex"], watch["needle"]["value"], 0, "pending", watch["needle"]["type"], watch_id, watch["currency"], watch["tx_fees"], timestamp, watch["address"]["type"], watch["address"]["value"], watch["memo"], watch["amount"], watch["expires"]))

            watch["db_id"] = tx.db.cur.lastrowid

    def update_watch(self, watch_id):
        watch = self.watches_by_id[watch_id]
        timestamp = int(time.time())
        with Transaction() as tx:
            sql = "UPDATE `transactions` SET `found_tx_hex`=?,`height`=?,`event`=?,`updated_at`=?,`address_type`=?,`amount`=?,`address_value`=? WHERE `id`=?"
            tx.execute(sql, (watch["found_tx_hex"], watch["height"], watch["event"], timestamp, watch["address"]["type"], watch["amount"], watch["address"]["value"], watch["db_id"]))

    def add_watch(self, currency, needle, callbacks, memo="", watch_id=None, expires=1):
        #Process needle.
        if type(needle) != dict:
            raise Exception("Needle needs to be type dict.")

        """
        Support watch by TXID because TXIDs are inherently unreliable (i.e. tx malleability) this relies on being able to retrieve the original tx_hex so the local client needs to know about the transaction. (Useful for monitoring transactions made by sendtoaddress anyway.)
        """
        rpc = self.coins[currency]["rpc"]["sock"]
        if needle["type"] == "txid":
            tx_hex = rpc.getrawtransaction(needle["value"])
            needle["type"] = "tx_hex"
            needle["value"] = tx_hex

        #Speed up tx_hex watches.
        event = None
        block = None
        height = 0
        if needle["type"] == "tx_hex":
            txid = calculate_txid(needle["value"])
            tx = CTransaction.deserialize(binascii.unhexlify(needle["value"]))
            input_total, output_total, tx_fees = calculate_tx_fees(self.coins, currency, needle["value"])
            amount = str(C(output_total))
            tx_fees = str(C(tx_fees))
            address = self.parse_address(tx, currency)[0]
        else:
            txid = "0"
            tx = None
            tx_fees = "0"
            amount = "0"
            if needle["type"] in self.address_types:
                address = {
                    "type": needle["type"],
                    "value": needle["value"]
                }
            else:
                address = {
                    "type": "unknown",
                    "value": ""
                }

        #Check tx_hex isn't already confirmed.
        if needle["type"] == "tx_hex":
            if rpc != None:
                try:
                    txid = calculate_txid(needle["value"])
                    ret = rpc.getrawtransaction(txid, 1)
                    if "confirmations" in ret:
                        if ret["confirmations"] >= self.confirmations:
                            if "confirm" in callbacks:
                                event = "confirm"
                                block = ret["blockhash"]
                                height = rpc.getblock(block)["height"]
                except JSONRPCException:
                    pass

        #Make callbacks dict valid.
        valid_callbacks = ["confirm", "mutate", "fraud", "arrival"]
        for valid_callback in valid_callbacks:
            if valid_callback not in callbacks:
                callbacks[valid_callback] = None

        #Generate id.
        if watch_id == None:
            watch_id = hashlib.sha256((str(time.time()) + currency + str(needle)).encode("ascii")).hexdigest()

        #Build watch.
        watch = self.watching[currency][watch_id] = {
            "currency": currency,
            "db_id": 0,
            "memo": memo,
            "txid": txid,
            "tx": tx,
            "tx_fees": tx_fees,
            "amount": amount,
            "found_tx_hex": "",
            "callback": callbacks,
            "needle": needle,
            "event": event,
            "confirmations": 0,
            "block": block,
            "height": height,
            "id": watch_id,
            "expires": expires,
            "address": address
        }

        print("Adding watch ")
        print(watch)

        #Update watch.
        if event == "confirm":
            self.do_callback(watch, callbacks[event], event, needle["value"], needle)
            return

        #Save watch.
        self.watches_by_id[watch_id] = watch
        self.save_watch(watch_id)

        #Store inputs.
        if needle["type"] == "tx_hex":
            for vin in tx.vin:
                input_txid = b2lx(vin.prevout.hash)
                input_index = vin.prevout.n
                if input_txid in self.inputs[currency]:
                    if input_index in self.inputs[currency][input_txid]:
                        raise Exception("Attempted double spend in add_watch.")
                    else:
                        self.inputs[currency][input_txid].append(input_index)
                else:
                    self.inputs[currency][input_txid] = [input_index]

        return watch_id


if __name__ == "__main__":

    print("TX monitor.")

    #Simulate double spend.
    def double_spend(tx_hex):
        tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
        tx.vin[0].scriptSig = CScript([OP_1])
        return b2x(tx.serialize())

    heights = {
        "dogecoin": 681793
    }
    monitor = TXMonitor(coins, confirmations=1, heights=heights, debug=1)

    callback = """
print(tx_hex)
print(event)
print("\a")
    """


    needle = {
        "type": "tx_hex",
        "value": double_spend("010000000151b4d186f7e3aadb5e8a1c000be10d54cae73d5c5725623089dae1a7f8ffe0b7010000006b4830450221009af9d298cf88d1b6175830fb5ba65a117b3a806486977c0278130ba57d24b91402204bccdf83cd6963c2f0c5c39c24e5cfcc8af0f57ae443229d863b7996ad77db5a012103fca371794b7a80eab1e22f4d7a5205207743fb42085338426cb5f438159cb8a6ffffffff0200ca9a3b000000001976a91424625666bc2816b34fb1f3d033c4a38f05dbb74588ac0032e426e50000001976a914a4581dfb7850bc4e6df10c01c9bd53349aadda2c88ac00000000")
    }

    needle = {
        "type": "p2sh",
        "value": "2N9Segut8bqkEf3JkSnE1Sx9zKm4KwPYvyP"
    }

    callbacks = {
        "arrival": callback,
        "confirm": callback,
        "mutate": callback,
        "fraud": callback
    }

    monitor.add_watch("dogecoin", needle, callbacks)

    while 1:
        monitor.check()
        time.sleep(0.001)


    exit()
    
    def confirm(event, found_tx_hex, expected_tx_hex):
        print("\a")
        print("------------")
        print("Tx confirmed!")
        print("Found: ")
        print(found_tx_hex)
        print()
        print("Expected: ")
        print(expected_tx_hex)

    def mutate(event, found_tx_hex, expected_tx_hex):
        print("------------")
        print("TX malluability occured.")
        print("Found: ")
        print(found_tx_hex)
        print()
        print("Expected: ")
        print(expected_tx_hex)

    def fraud(event, found_tx_hex, expected_tx_hex):
        print("------------")
        print("Tx double spend occured.")
        print("Found: ")
        print(found_tx_hex)
        print()
        print("Expected: ")
        print(expected_tx_hex)

    def arrival(event, found_tx_hex, expected_tx_hex):
        print("------------")
        print("Transaction was found in mem pool.")
        print("Found: ")
        print(found_tx_hex)
        print()
        print("Expected: ")
        print(expected_tx_hex)

    #monitor.add_watch("litecoin", "0100000001105588788a3c615d539b047a8abce1842fa196cae2bfdcdaa24dcf7ae8d38423000000006c493046022100cb67597fe830e62b1021fe87f7babd007cdc281a14fb81bab9380210bf2f24c202210087932adfa4a5c278806f67430c62851d1eea0b94bdd5a8a6345e362691c182860121038e537ec0d333d3e73a0795ae424d75a47defd6945966ff9c772bd9b5a891dddbffffffff02cd8a9b00000000001976a914c623bccb8aabbca852c403a6a0cab93da26ce75088ac20a10700000000001976a914457d6a3e4f28523cff18863f9f603ad25ff2060788ac00000000", confirm, mutate, fraud, arrival)

    #monitor.add_watch("bitcoin", double_spend("0100000001c41fcf48e5b806754ab8b240feb42b1dcc347d4431daf34ff9eab91ef3c27e4c010000006b483045022100d432e776eaa7e29253714534eac12c6a61729040b4dce75a5cfcf975058bca510220731d651ccd01fab49d7e3bd9df3dbfd3d31e00d161d473d246fe4422e211ba66012103a0a2313aaae7175f7e140fb4a4eebd1f4a41186c4d6cee770e2c69495f4a9ed7ffffffff02f4c41900000000001976a91485671ec6e6096b789726206448dc260f225f358f88ac20a10700000000001976a914594c3afe0fde69e0fc1f1557fcce41d263ece96e88ac00000000"), confirm, mutate, fraud, arrival)

    #{'4c7ec2f31eb9eaf94ff3da31447d34cc1d2bb4fe40b2b84a7506b8e548cf1fc4': [1]}

    #monitor.add_watch("bitcoin", "01000000018d6ebea637ac3919210e60db170cabb7cee6e6e372a9e6fd293b4fe5092bcb99000000006b4830450220067b13ffd9102c9611683c03fcd80394e4c97616c007f177f555198ecbdefb57022100f7b1bbbb1820d2e58e94408c7c505cb63768831773965e32f659acd64ea57cd101210327ffbcc796a0bdc64738111e4d011471abcc58882c659090a79ab8dcadd66d46ffffffff027cc50c02000000001976a91462f260e3b361fb44eb350235351e5e202b605e3d88ac20a10700000000001976a914594c3afe0fde69e0fc1f1557fcce41d263ece96e88ac00000000", confirm, mutate, fraud, arrival)

    #'99cb2b09e54f3b29fde6a972e3e6e6ceb7ab0c17db600e211939ac37a6be6e8d': [0]

    events = {
        "confirm": confirm,
        "mutate": mutate,
        "fraud": fraud
    }
    monitor.add_watch("dogecoin", "010000000129e6f9a9a8869e0b1cbfb8e870c6bd9e3d6cb12f97d979560a44614e549e8be3000000006a47304402203a5e3b4099bebc83e79442180486f0ad4f29543684c905e8821ab4d7d123d385022046de7abbace646e2e2fe649ae973a97c7c7439afde918b90e1c0e0d8a667983f012103b244c985f624e7095f5f3bb052453d5f06748c916bac51afea04a2aa386148bfffffffff02608c69dc481b00001976a9141d5507eb2cbfd8e1eb1b18ab8190b540f0520dc288aca09102030000000017a914f8f8a1aeb6899f0abced7978aeaaa0532c20ed6f8700000000", events)


    while 1:
        monitor.check()
        time.sleep(1)


from .address import Address
