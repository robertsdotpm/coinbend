import binascii
import bitcoin
import decimal
import hashlib
import random
import datetime
import copy
import time

from bitcoin import SelectParams
from bitcoin.core import b2x, b2lx, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret, CKey
from decimal import Decimal

from .globals import *
from .currency_type import *
from .json_rpc import *
from .coinlib import *
from .lib import *
from .ecdsa_crypt import *
from .exchange_rate import *
from .private_key import *
from .green_address import *
from .address import *
from .database import *

def find_microtransfer(needle, trades):
    #Needle = a contract_hash to find.
    if needle == None:
        raise Exception("Invalid contract hash in find_microtransfer")

    for our_trade in trades:
        contracts = our_trade.contract_factory.contracts
        for contract_hash in list(contracts):
            if contract_hash == needle:
                return contracts[contract_hash]

    return None

def validate_setup_tx(config, tx_hex, ecdsa_1, ecdsa_2, sig_1, sig_2, sig_3=None, collateral_info=None, trade_fee=C(0)):
    #Init.
    ecdsa_encrypted = ECDSACrypt(config["green_address_server"]["encrypted_key_pair"]["pub"])
    ecdsa_offline = ECDSACrypt(config["green_address_server"]["offline_key_pair"]["pub"])
    ecdsa_fee = ECDSACrypt(config["fee_key_pair"]["pub"])
    tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))

    #Check txin is as expected.
    if len(tx.vin) != 1:
        return -1
    deposit_txid = b2lx(tx.vin[0].prevout.hash)

    #Check transaction is final.
    if tx.vin[0].nSequence != 0xffffffff:
        return -5
    if tx.nLockTime != 0:
        return -6

    #Determine contract outs.
    if len(tx.vout) < 2:
        return -3
    contract_vouts = tx.vout[1:]
    change_script_pub = CScript([
        OP_DUP,
        OP_HASH160,
        Hash160(ecdsa_1.get_public_key("bin")),
        OP_EQUALVERIFY,
        OP_CHECKSIG
    ])
    if contract_vouts[-1].scriptPubKey == change_script_pub:
        change_vout = contract_vouts.pop()
        change_total = Decimal(str_money_value(change_vout.nValue))
    else:
        change_vout = None
        change_total = Decimal(0)

    #Total contract sums.
    contract_total = Decimal(0)
    for contract_vout in contract_vouts:
        contract_total += Decimal(str_money_value(contract_vout.nValue))

    #Validate fee output.
    fee_script_pub = CScript([
        OP_DUP,
        OP_HASH160,
        Hash160(ecdsa_fee.get_public_key("bin")),
        OP_EQUALVERIFY,
        OP_CHECKSIG
    ])
    fee_vout = tx.vout[0]
    fee_total = Decimal(str_money_value(fee_vout.nValue))
    if fee_vout.scriptPubKey != fee_script_pub:
        return -4

    #Validate contract collateral.
    if collateral_info != None:
        remaining = collateral_info.copy()
        collateral_total = C(0)
        for pub_key_1 in list(collateral_info):
            #Check their ecdsa 1 signature.
            ecdsa_them = []
            ecdsa_pair = ECDSACrypt(pub_key_1)
            sig = collateral_info[pub_key_1]["sig_1"]
            chunk_size = collateral_info[pub_key_1]["chunk_size"]
            arbiter_pub = collateral_info[pub_key_1]["pub_arbiter"]
            msg = "%s %s" % (chunk_size, arbiter_pub)
            if not ecdsa_pair.valid_signature(sig, msg):
                continue
            else:
                ecdsa_them.append(ecdsa_pair)

            #Check their ecdsa 2 signature.
            ecdsa_pair = ECDSACrypt(collateral_info[pub_key_1]["pub_2"])
            sig = collateral_info[pub_key_1]["sig_2"]
            if not ecdsa_pair.valid_signature(sig, msg):
                continue
            else:
                ecdsa_them.append(ecdsa_pair)

            #Find their contract in setup_tx.
            for vout in contract_vouts:
                ecdsa_us = [ecdsa_1, ecdsa_2]
                ecdsa_arbiter = ECDSACrypt(arbiter_pub)
                redeem_script = bond_redeem_script(ecdsa_us, ecdsa_them, ecdsa_arbiter)
                redeem_script_hash160 = hash160_script(redeem_script)
                p2sh_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])
                if vout.scriptPubKey != p2sh_script_pub_key:
                    continue
                else:
                    #Update remaining structure to indicate this validated.
                    if pub_key_1 in remaining:
                        del remaining[pub_key_1]

                #Update collateral amount.
                collateral_total += collateral_info[pub_key_1]["chunk_size"]

        #Check the fee amount is valid given claimed collaterals.
        if not len(list(remaining)):
            total_coins = C(fee_total + contract_total)
            expected_fee = collateral_total + ((total_coins - C(change_total)) * trade_fee)
            print(collateral_total)
            print(expected_fee)
            print(fee_total)
            if expected_fee != C(fee_total):
                print("Fee validation did not parse!")
                return -40
            else:
                print("fdsfdsdfsdf num validation was all successful.")

    #Calculate txid.
    setup_txid = calculate_txid(b2x(tx.serialize()))        

    #Check setup tx works.
    setup_signed_tx = None
    setup_signed_txid = None
    if sig_3 != None or (sig_1 == None and sig_2 == None and sig_3 == None):
        redeem_script = green_redeem_script(ecdsa_1, ecdsa_2, ecdsa_encrypted, ecdsa_offline)
        tx_hex = b2x(tx.serialize())
        ret = check_setup_works(tx_hex, redeem_script, sig_1, sig_2, sig_3)
        if ret != None:
            setup_signed_tx = CTransaction.deserialize(binascii.unhexlify(ret["tx_hex"]))
            setup_signed_txid = ret["txid"]

    ret = {
        "deposit": {
            "txid": deposit_txid
        },

        "setup": {
            "tx": tx,
            "txid": setup_txid,
            "sig_1": sig_1,
            "sig_2": sig_2,
            "sig_3": sig_3,
            "signed": {
                "tx": setup_signed_tx,
                "txid": setup_signed_txid
            }
        },

        "contract": {
            "vouts": contract_vouts,
            "total": contract_total
        },

        "fee": {
            "vout": fee_vout,
            "total": fee_total
        },

        "change": {
            "vout": change_vout,
            "total": change_total
        }
    }

    return ret

def bond_redeem_script(ecdsa_us, ecdsa_them, ecdsa_arbiter, actor="us"):
    """
    Setup transaction uses p2sh format for contract output with the redeem script being a multi-signature transaction using 3 of 4.
    """
   
    if actor == "us":
        script = CScript([
            3,
            ecdsa_us[0].get_public_key("bin"),
            ecdsa_us[1].get_public_key("bin"),
            ecdsa_them[0].get_public_key("bin"),
            ecdsa_arbiter.get_public_key("bin"),
            4,
            OP_CHECKMULTISIG,
        ])
    else:
        script = CScript([
            3,
            ecdsa_them[0].get_public_key("bin"),
            ecdsa_them[1].get_public_key("bin"),
            ecdsa_us[0].get_public_key("bin"),
            ecdsa_arbiter.get_public_key("bin"),
            4,
            OP_CHECKMULTISIG,
        ])

    return {
        "bin": script,
        "hex": binascii.hexlify(script).decode("ascii")
    }

def calculate_chunk_size(amount, dollars_worth):
    if amount.currency in dollars_worth:
        dollars_worth = C(dollars_worth[amount.currency])
    else:
        dollars_worth = C("0")

    #Dollars worth couldn't calculated.
    if not dollars_worth:
        return amount * C("0.05")

    #That's all the money I've got - trade isn't a dollars' worth.
    if dollars_worth >= amount:
        return amount * C("0.05")

    #A dollars' worth is still comparatively a lot to lose for this trade. 
    if Decimal(str(dollars_worth)) / Decimal(str(amount)) >= Decimal("1"):
        return amount * C("0.05")

    return dollars_worth

def calculate_fees(s):
    pass

def check_setup_works(tx_hex, redeem_script, owner_first_sig, owner_second_sig, third_party_sig):
    try:
        tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
        redeem_script_hash160 = hash160_script(redeem_script)

        if owner_first_sig != None and owner_second_sig != None and third_party_sig != None:
            tx.vin[0].scriptSig = CScript([OP_0, owner_first_sig, owner_second_sig, third_party_sig, redeem_script["bin"]])
        p2sh_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])

        VerifyScript(tx.vin[0].scriptSig, p2sh_script_pub_key, tx, 0, (SCRIPT_VERIFY_P2SH,))
        signed_tx_hex = b2x(tx.serialize())
        return {
            "tx_hex": signed_tx_hex,
            "txid": calculate_txid(signed_tx_hex)
        }
    except Exception as e:
        error = parse_exception(e)
        log_exception(error_log_path, error)
        print(error)
        print("Check setup works failed.")
        print(e)
        return None

def sign_setup_tx(tx_hex, redeem_script, ecdsa):
    tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
    sighash = SignatureHash(redeem_script["bin"], tx, 0, SIGHASH_ALL)

    print(b"Signing = " + sighash)
    
    print(ecdsa.get_public_key())

    seckey = CBitcoinSecret.from_secret_bytes(ecdsa.get_private_key("bin"), compressed=True)
    sig = seckey.sign(sighash) + bytes([SIGHASH_ALL])
    print(b"Pub key = " + ecdsa.get_public_key("bin"))

    print(b"Sig = " + sig)
    print()
    return sig

class MicrotransferFactory():
    def __init__(self, green_address, coins, config):
        self.max_contract_limit = 10
        self.our_tx_fee = C(0)
        self.their_tx_fee = C(0)
        self.green_address = green_address
        self.coins = coins
        self.config = config
        self.trade = self.green_address.trade.copy()
        self.instance_id = None
        self.state = "pending_ready"
        self.contracts = {}
        self.setup = {
            "tx_hex": None,
            "txid": None,
            "signed": {
                "tx_hex": None,
                "txid": None
            }
        }

        self.refund = {
            "tx_hex": None,
            "txid": None,
            "signed": {
                "tx_hex": None,
                "txid": None
            }
        }

        #Observed setup_txids for various contracts.
        self.setup_txids = {}

        #Observed setup txs for various contracts.
        self.setups = {}

        #Observed refund hexs for various contracts.
        self.refunds = {}

        #Signed proof of chunk size from contract participants.
        self.collateral_info = {}

        #Apply trade fees.
        self.trade_fee = C(self.config["trade_fee"])
        self.trade.apply_trade_fee(self.trade_fee)
        self.total = C(0)

        #Store arbiters.
        self.ecdsa_arbiters = []
        for arbiter in self.config["arbiter_key_pairs"]:
            self.ecdsa_arbiters.append(ECDSACrypt(arbiter["pub"]))

    def update_state(self, state):
        self.state = state

    def add_contract(self, contract_hash, trade, ecdsa_us, ecdsa_them, our_address, their_address, chunk_sizes, ntp, matched=None):
        assert(trade.action == self.trade.action), "Contract trades must have same action (direction) as green address"

        """
        Todo: There's a point where the slots get too small to transfer (when there isn't enough left for micro-collateral + standard TX fee.) If that's the case, throw an exception and allocate the difference as change for the setup.
        """
        if self.trade.remaining < trade.remaining:
            print(self.trade.remaining)
            print(trade.remaining)
            raise Exception("No more slots remain for contract factory.")

        """
        Most cryptocurrencies charge fees depending on TX size. Too many contracts from one setup transaction == greater TX size == greater tx fee (which we don't have === no confirmations. Check we're not going on the limit.
        """
        vout = len(self.contracts) + 1
        if vout > self.max_contract_limit:
            raise Exception("Too many contracts for one setup TX.")

        #Create contract.
        contract = MicrotransferContract(
            self,
            contract_hash,
            trade,
            vout,
            ecdsa_us,
            ecdsa_them,
            our_address,
            their_address,
            self.coins,
            self.config,
            chunk_sizes,
            ntp,
            matched
        )

        """
        If the slot size for the change output ends up being less than the dust threshold limit as a result of consuming more coins the the TX won't be get confirmations. Check that we're not forcing a change amount that can't be broadcast.
        """
        new_remaining = self.trade.remaining - trade.remaining
        if new_remaining and new_remaining < self.coins[trade.to_send.currency]["dust_threshold"]:
            print(new_remaining)
            raise Exception("Resulting change output for microtransfer contract is bellow the dust threshold.")

        #Do a pseudo-match for bookkeeping.
        self.trade.remaining -= trade.remaining
        self.total += trade.remaining
        #Todo: use to.send
        
        #Record contract.
        self.contracts[contract_hash] = contract
        contract.save()

        #Return reference.
        return contract

    def remove_contract(self, contract_hash):
        if contract_hash not in self.contracts:
            raise Exception("Contract not found in contract factory.")

        #Undo reserved slot amount.
        self.trade.remaining += contract.trade.remaining
        self.total -= contract.trade.remaining

        #Remove contract.
        del self.contracts[contract_hash]

    def build_setup(self):
        #Get wallet balance.
        currency = self.trade.to_send.currency
        coin_rpc = self.coins[currency]["rpc"]["sock"]
        balance = C(coin_rpc.getbalance())
        self.tx_fee_amount = self.coins[currency]["tx_fee"]
        
        #Check we have enough.
        if balance < self.trade.to_send:
            raise Exception("Insufficent balance to cover fund.") 
        
        #List unclaimed inputs.
        self.green_address.load_inputs()
        unspent_inputs = self.green_address.inputs

        #Check unclaimed outputs go to the right green address.
        global tx_monitor
        deposit_tx = self.green_address.deposit_tx_hex
        print(deposit_tx)
        deposit_tx = CTransaction.deserialize(binascii.unhexlify(deposit_tx))
        print(deposit_tx)
        ret = tx_monitor.parse_address(deposit_tx, currency)
        print(ret)
        ret = ret[0]
        print(ret)
        if ret["type"] != "p2sh":
            raise Exception("Invalid green address deposit tx.")
        else:
            p2sh_index = ret["vout"]
            green_address_hash = deconstruct_address(self.green_address.address)["hash"]
            if deposit_tx.vout[p2sh_index].scriptPubKey != CScript([OP_HASH160, green_address_hash, OP_EQUAL]):
                raise Exception("Unexpected green address output.")
        
        #Setup tx inputs.
        txins = []
        green_total = C("0")
        indexes = []
        for unspent_input in unspent_inputs:
            #Skip outputs that don't satisfy min confirmations.
            confirmations = int(self.config["confirmations"])
            if unspent_input["confirmations"] < confirmations:
                continue

            #Skip non p2sh outputs.
            if unspent_input["vout"] != p2sh_index:
                continue
            
            #Build new txin.
            txid = lx(unspent_input["txid"])
            vout = unspent_input["vout"]
            txin = CTxIn(COutPoint(txid, vout))
            txins.append(txin)
            green_total += C(unspent_input["amount"])

            break
        
        #Insufficent funds.
        if green_total < self.green_address.trade.to_send:
            print("Exception .. insufficent funds.")
            print(green_total)
            print(self.green_address.trade.to_send)
            raise Exception("Not enough valid inputs to fund contract.")

        #Calculate collateral amount.
        total = C(0)
        collateral = C(0)
        to_send = C(0)
        for contract_hash in list(self.contracts):
            contract = self.contracts[contract_hash]
            collateral += contract.our_chunk_size
            to_send += contract.upload_amount + contract.our_chunk_size + self.tx_fee_amount
            print("Our chunk size: " + str(contract.our_chunk_size))

        """
        Trade fees are initially applied based on being able to match 100%. If there's change it means not everything was matched and hence you're being charged fees for coins that aren't even being traded. The code bellow recalculates the fees.
        """
        fees = self.trade.fees
        to_send += fees
        if to_send < self.green_address.trade.to_send:
            print("Fees reduced.")
            ceiling = self.green_address.trade.to_send - to_send 
            fees = ceiling * self.trade_fee
            #I'm not sure this is correct.
        print("Trade fees: " + str(fees))

        #Add fees to collateral.
        collateral += fees
        print("Collateral: " + str(collateral))
        total += collateral
        
        #Collateral / fee output.
        txouts = []
        ecdsa_fee = ECDSACrypt(self.config["fee_key_pair"]["pub"])
        collateral_script_pub_key = CScript([OP_DUP, OP_HASH160, Hash160(ecdsa_fee.get_public_key("bin")), OP_EQUALVERIFY, OP_CHECKSIG])
        txouts.append(CTxOut(collateral.as_decimal * COIN, collateral_script_pub_key))

        #Contract outputs.
        for contract_hash in list(self.contracts):
            contract = self.contracts[contract_hash]
            redeem_script = bond_redeem_script(contract.ecdsa_us, contract.ecdsa_them, self.ecdsa_arbiters[0])
            redeem_script_hash160 = hash160_script(redeem_script)
            p2sh_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])
            contract_amount = contract.upload_amount + self.tx_fee_amount
            print("Contract amount: " + str(contract_amount))
            txouts.append(CTxOut(contract_amount.as_decimal * COIN, p2sh_script_pub_key))
            total += contract_amount

        #Change output.
        if total < self.green_address.trade.to_send:
            change = self.green_address.trade.to_send - total
            if change > C("0"):
                change_script_pub_key = CScript([OP_DUP, OP_HASH160, Hash160(self.ecdsa_1.get_public_key("bin")), OP_EQUALVERIFY, OP_CHECKSIG])
                txouts.append(CTxOut(change.as_decimal * COIN, change_script_pub_key))
            
        #Build unsigned transaction.
        tx = CTransaction(txins, txouts)

        #Return unsigned transaction hex.
        tx_hex = b2x(tx.serialize())
        txid = calculate_txid(tx_hex)
        our_first_sig = sign_setup_tx(tx_hex, self.green_address.redeem_script, self.green_address.ecdsa_1)
        our_second_sig = sign_setup_tx(tx_hex, self.green_address.redeem_script, self.green_address.ecdsa_2)

        self.setup["tx_hex"] = tx_hex
        self.setup["txid"] = txid
        self.setup["sig_1"] = our_first_sig
        self.setup["sig_2"] = our_second_sig
        return {
            "tx_hex": tx_hex,
            "txid": txid,
            "first_sig": our_first_sig,
            "second_sig": our_second_sig
        }

class MicrotransferContract():
    def __init__(self, factory, contract_hash, trade, vout, ecdsa_us, ecdsa_them, our_address, their_address, coins, config, chunk_sizes, ntp, matched=None):
        self.id = 0
        self.details = {}
        self.factory = factory
        self.contract_hash = contract_hash
        self.trade = trade
        self.vout = vout
        self.coins = coins
        self.config = config
        self.ecdsa_us = ecdsa_us
        self.ecdsa_them = ecdsa_them
        self.chunk_sizes = chunk_sizes
        self.ntp = int(ntp)
        self.min_confirms = 0 #Todo change this.
        self.matched = matched
        self.our_address = our_address
        self.their_address = their_address

        if "our_setup" not in self.details:
            self.details["our_setup"] = {
                "txid": None
            }
        if "our_refund" not in self.details:
            self.details["our_refund"] = {}
        if "our_download" not in self.details:
            self.details["our_download"] = {
                "tx_hex": ""
            }

        #Setup Python Bitcoinlib on right network
        #Mostly import for address validation.
        if self.config["testnet"]:
            bitcoin.SelectParams('testnet')

        #Set decimal precision.
        getcontext().prec = 8

        #What are we doing?
        if self.trade.to_send == self.trade.amount:
            #Seller.
            self.our_chunk_size = chunk_sizes["seller"]
            self.their_chunk_size = chunk_sizes["buyer"]
        else:
            #Buyer.
            self.our_chunk_size = chunk_sizes["buyer"]
            self.their_chunk_size = chunk_sizes["seller"]
        self.send_coin_rpc = self.coins[self.trade.to_send.currency]["rpc"]["sock"]
        self.recv_coin_rpc = self.coins[self.trade.to_recv.currency]["rpc"]["sock"]

        #Check chunk size.
        our_ceiling = self.our_chunk_size + self.factory.our_tx_fee
        their_ceiling = self.their_chunk_size + self.factory.their_tx_fee
        if our_ceiling >= self.trade.to_send:
            raise Exception("Sending amounts too small for contract.")
        if their_ceiling >= self.trade.to_recv:
            raise Exception("Recv amounts too small for contract.")

        #Calculate fees.
        self.upload_amount = self.trade.to_send - our_ceiling
        self.download_amount = self.trade.to_recv - their_ceiling

        """
        If this slot is less than the dust threshold limit then the resulting download TX won't be able to be claimed. Check that it leaves enough coins.
        """
        if self.upload_amount < self.coins[self.trade.to_send.currency]["dust_threshold"]:
            raise Exception("Microtransfer contract upload amount is less than the dust threshold.")
        if self.download_amount < self.coins[self.trade.to_recv.currency]["dust_threshold"]:
            raise Exception("Microtransfer contract download amount is less than the dust threshold.")

        """
        Contract max time. This is the time that has to be waited for
        before a refund can be claimed.
        """
        self.contract_duration = 2 * 60 * 60

        #Locktime is unsigned int 4, unix timestamp in little endian format.
        #(Conversion to little endian is handled by the library already.)
        self.nlock_time = datetime.datetime.fromtimestamp(self.ntp) + datetime.timedelta(seconds=self.contract_duration)
        self.nlock_time = int(time.mktime(self.nlock_time.timetuple()))

        #Generate change address.
        self.change_address = self.send_coin_rpc.getnewaddress()

    def save(self):
        timestamp = int(time.time())
        with Transaction() as tx:
            sql = "INSERT INTO `microtransfers` (`status`, `action`, `amount`, `ppc`, `base_currency`, `quote_currency`, `upload_amount`, `download_amount`, `created_at`, `green_address`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            tx.execute(sql, (self.trade.status, self.trade.action, str(self.trade.amount), str(self.trade.ppc), self.trade.pair["base"], self.trade.pair["quote"], str(self.upload_amount), str(self.download_amount), timestamp, self.factory.green_address.address))
            self.id = tx.db.cur.lastrowid

    def update(self, status=None):
        print("Updating microtransfer contract.")
        print("Id = " + str(self.id))
        print("Status = " + str(status))
        timestamp = int(time.time())
        download_txid = calculate_txid(self.details["our_download"]["tx_hex"])
        with Transaction() as tx:
            sql = "UPDATE `microtransfers` SET `download_tx_hex`=?,`sent`=?,`recv`=?,`updated_at`=?,`download_txid`=?"
            if status != None:
                sql += ",`status`=?"
            sql += " WHERE `id`=?"

            if status != None:
                tx.execute(sql, (self.details["our_download"]["tx_hex"], str(self.trade.sent), str(self.trade.recv), timestamp, download_txid, status, self.id))
            else:
                tx.execute(sql, (self.details["our_download"]["tx_hex"], str(self.trade.sent), str(self.trade.recv), timestamp, download_txid, self.id))

    def build_refund_tx(self, setup_tx_id, refund_amount=None):
        #Check refund amount.
        if refund_amount != None:
            if refund_amount > self.trade.to_send:
                raise Exception("Invalid refund amount.")

        #Create redeem script.    
        redeem_script = bond_redeem_script(self.ecdsa_us, self.ecdsa_them, self.factory.ecdsa_arbiters[0])
        
        #Generate p2sh script pub key.
        redeem_script_hash160 = hash160_script(redeem_script)

        txin_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])

        #Setup tx inputs.
        txid = lx(setup_tx_id)
        txin = CTxIn(COutPoint(txid, self.vout))
        txouts = []

        #Our output.
        our_address = deconstruct_address(self.change_address)["hash"]
        our_pub_key = CScript([OP_DUP, OP_HASH160, our_address, OP_EQUALVERIFY, OP_CHECKSIG])

        #Their output.
        their_address = deconstruct_address(self.their_address)["hash"]
        their_pub_key = CScript([OP_DUP, OP_HASH160, their_address, OP_EQUALVERIFY, OP_CHECKSIG])

        #Append outputs.
        if refund_amount == None:
            #Inital full refund.
            remaining = self.upload_amount
            txouts.append(CTxOut(remaining.as_decimal * COIN, our_pub_key))
        else:
            """
            Micro-payment channel i.e. the contract. 

            The refund amount leaves "room" for a TX fee so you just do normal calculations and the difference constitutes the TX fee.
            """
            remaining = self.upload_amount - refund_amount
            if remaining > C("0"):
                txouts.append(CTxOut(remaining.as_decimal * COIN, our_pub_key))
            txouts.append(CTxOut(refund_amount.as_decimal * COIN, their_pub_key))

        #Create unsigned transaction.
        if refund_amount == None:
            txin.nSequence = 0 #Enable ntimelocks.
            tx = CTransaction([txin], txouts, self.nlock_time)
        else:
            txin.nSequence = 0xffffffff #Make transaction final!
            tx = CTransaction([txin], txouts)

        #Return unsigned transaction hex.
        tx_hex = b2x(tx.serialize())
        txid = calculate_txid(tx_hex)
        our_first_sig = self.sign_refund_tx(tx_hex, 1)
        our_second_sig = self.sign_refund_tx(tx_hex, 2)
        return {
            "tx_hex": tx_hex,
            "txid": txid,
            "first_sig": our_first_sig,
            "second_sig": our_second_sig
        }

    def check_refund_works(self, tx_hex, owner_first_sig, owner_second_sig, recipient_sig, actor):
        global error_log_path

        try:
            tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
            redeem_script = bond_redeem_script(self.ecdsa_us, self.ecdsa_them, self.factory.ecdsa_arbiters[0], actor)
            redeem_script_hash160 = hash160_script(redeem_script)

            print(tx_hex)
            print(redeem_script)

            tx.vin[0].scriptSig = CScript([OP_0, owner_first_sig, owner_second_sig, recipient_sig, redeem_script["bin"]])
            p2sh_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])
            print(redeem_script_hash160)

            VerifyScript(tx.vin[0].scriptSig, p2sh_script_pub_key, tx, 0, (SCRIPT_VERIFY_P2SH,))
            signed_tx_hex = b2x(tx.serialize())
            return {
                "tx_hex": signed_tx_hex,
                "txid": calculate_txid(signed_tx_hex)
            }
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)
            print("Check refund failed.")
            return None

    def sign_refund_tx(self, tx_hex, key_no=1, actor="us"):
        key_no -= 1
        if key_no == 0:
            ecdsa = self.ecdsa_us[0]
        if key_no == 1:
            ecdsa = self.ecdsa_us[1]
        tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
        sighash = SignatureHash(bond_redeem_script(self.ecdsa_us, self.ecdsa_them, self.factory.ecdsa_arbiters[0], actor)["bin"], tx, 0, SIGHASH_ALL)
        seckey = CBitcoinSecret.from_secret_bytes(ecdsa.get_private_key("bin"), compressed=True)
        sig = seckey.sign(sighash) + bytes([SIGHASH_ALL])
        return sig

    def adjust_refund_tx(self, our_setup_txid, their_setup_tx_hex, their_refund_tx_hex, received_tx_hex=None, their_first_sig=None, their_second_sig=None):
        #Calculate chunk sizes.
        remaining = self.upload_amount - self.trade.sent
        send_chunk_size = self.our_chunk_size
        if send_chunk_size > remaining:
            send_chunk_size = remaining
        remaining = self.download_amount - self.trade.recv
        recv_chunk_size = self.their_chunk_size
        if recv_chunk_size > remaining:
            recv_chunk_size = remaining

        #Validate transactions.
        if received_tx_hex != None and their_first_sig != None and their_second_sig != None:
            #Check their refund spends the output of the bond.
            their_refund_tx = CTransaction.deserialize(binascii.unhexlify(their_refund_tx_hex))
            their_setup_txid = calculate_txid(their_setup_tx_hex)
            if reverse_hex(binascii.hexlify(their_refund_tx.vin[0].prevout.hash).decode("utf-8")) != their_setup_txid:
                print("11111")
                return None
            else:
                """
                try:
                    #Ensure the bond transaction has been broadcast.
                    self.recv_coin_rpc.sendrawtransaction(their_bond_tx_hex)

                    #(Subsequent code will fail since bond has only just been broadcast.)
                    #return None
                except Exception as e:
                    #Transaction already in block chain.
                    pass
                """

            #Check our received payment is as expected.
            unsigned_tx = CTransaction.deserialize(binascii.unhexlify(received_tx_hex))
            expected = self.trade.recv + recv_chunk_size

            #Check transaction input.
            their_alleged_setup_txid = reverse_hex(binascii.hexlify(unsigned_tx.vin[0].prevout.hash).decode("utf-8"))
            if their_alleged_setup_txid != their_setup_txid:
                #Give them the benefit of the doubt - look for tx malluability.
                alleged_setup_tx_hex = recv_coin_rpc.getrawtransaction(their_alleged_setup_txid)
                if not compare_transactions(alleged_setup_tx_hex, their_setup_tx_hex):
                    print("22222222@")
                    return None

            #This is what our output -should- look like.
            our_address = deconstruct_address(self.our_address)["hash"]
            our_pub_key = CScript([OP_DUP, OP_HASH160, our_address, OP_EQUALVERIFY, OP_CHECKSIG])

            #Check an output goes to us with expected amount.
            amount_found = 0
            for output in unsigned_tx.vout:
                print(output.scriptPubKey)
                print(our_pub_key)
                if output.scriptPubKey == our_pub_key:
                    amount_found = Decimal(str_money_value(output.nValue))
                    break
            if not amount_found:
                print(our_pub_key)
                print(unsigned_tx.vout)
                print("333333333333")
                return None
            else:
                #Check amount.
                if amount_found < expected.as_decimal:
                    print("43535345346")
                    print(amount_found)
                    print(expected.as_decimal)
                    return None

            #Check transaction isn't time locked.
            if unsigned_tx.nLockTime:
                print("4444444444")
                return None

            #Check sequences are final.
            for input in unsigned_tx.vin:
                if input.nSequence != 0xffffffff:
                    print("55555555555")
                    return None

            #Check transaction can be spent.
            our_first_sig = self.sign_refund_tx(received_tx_hex, 1, "them")
            ret = self.check_refund_works(received_tx_hex, their_first_sig, their_second_sig, our_first_sig, "them")
            if ret == None:
                print("6666666666666")
                return None
            self.details["our_download"] = ret
        else:
            #The first call to this function has nothing to evaluate -- you are receiving nothing.
            recv_chunk_size = 0

        #Adjust refund.
        refund_amount = self.trade.sent + send_chunk_size
        print("sdfsdfsdf--------")
        print(refund_amount)
        refund_tx_hex = self.build_refund_tx(our_setup_txid, refund_amount)["tx_hex"]
        self.trade.sent += send_chunk_size
        self.trade.recv += recv_chunk_size

        #Save details.
        self.update()

        #Is transfer complete? I.e. no change = transfer complete.
        if send_chunk_size == C(0) and recv_chunk_size == C(0):
            #I liek chocolate milk.
            return 1
        
        #Return result.
        our_first_sig = self.sign_refund_tx(refund_tx_hex, 1)
        our_second_sig = self.sign_refund_tx(refund_tx_hex, 2)
        return {
            "tx_hex": refund_tx_hex,
            "first_sig": our_first_sig,
            "second_sig": our_second_sig
        }

    def set_refund(self, refund_tx_hex, our_first_sig, our_second_sig, their_sig):
        self.details["our_refund"] = {
            "tx_hex": calculate_txid(refund_tx_hex),
            "first_sig": our_first_sig,
            "second_sig": our_second_sig,
            "their_sig": their_sig
        }

    def build_mediation_tx(self):
        pass

    
if __name__ == "__main__":
    """
    Trade fees need to be taken from the sending / correct side. Which side? Does this ruin the design?

    Fees need to be changed to be applied to the sending side ... I think~ this should fix the problem.
    """

    ecdsa_encrypted = ECDSACrypt("AxdpCB9QfrUu3TVvZ+s8L7nVwg4Rmd/nq1o4gWRMqsw3", "ylx2vnbyZBN3/d4Zq9GWS6suDWiQ3CW4LyMGaM91dNA=")

    alice_trade = Trade("buy", "0.05", ["bitcoin", "litecoin"], "0.5")
    bob_trade = Trade("sell", "0.05", ["bitcoin", "litecoin"], "0.5")

    #Apply trade fees.
    trade_fee = C(config["trade_fee"])
    alice_trade.apply_trade_fee(trade_fee)
    bob_trade.apply_trade_fee(trade_fee)


    alice_ecdsa_1 = ECDSACrypt("AjvilWL8iA1wTTYaNbalXevj68ioTfWBAQBGO6zRCZO+", "NZJ8R0otu9koNztEe5W9TyarDnrN4kq7YkKgQjaUZxs=")
    alice_ecdsa_2 = ECDSACrypt("Ar/bCBziHi8t2+7Ba7M0PBaYhzn6BFH2oaMwD7MbXO2i", "gIRzjbSVcpR9LDTraZ1T5BUlcz50c7ODrijNzHZX3Bw=")


    bob_ecdsa_1 = ECDSACrypt("AqTNIOfHuY6JMJCCPoVSUZ7rUDbb1kaQymKheBBxaJDw", "MUOuPMF+H2MBVJV6HMVpmC4Zw5XUE2r95cPtSsPl8/U=")


    bob_ecdsa_2 = ECDSACrypt("Aq3GnzfUdHq2C94tKrWeerXlhDIG+zCqRUB9qHo9k6N6", "Noswa7Fv7Fv8lPQq23K9W9KOVFUH60YzQnGJ+XbXPEM=")

    #class MicrotransferFactory(): def __init__(self, green_address, coins, config):

    alice_green_address = GreenAddress(alice_trade, alice_ecdsa_1, alice_ecdsa_2, ecdsa_encrypted, coins, config, address="2N4tAw1TWByq2wQYoGFH3hMhkQqMjxax2kQ", deposit_txid="0c61655261a37fde3f3188ec89183e9cd8063eaf027a15db5c4a17eaf339959e")



    alice_factory = MicrotransferFactory(alice_green_address, coins, config)
    alice = alice_factory.add_contract(alice_trade, [alice_ecdsa_1, alice_ecdsa_2], [bob_ecdsa_1, bob_ecdsa_2], [C("0.00000001"), C("0.00000001")])

    alice_setup = alice_factory.build_setup()

    exit()

    #alice = MicrotransferContract(alice_trade, alice_green_address, [alice_ecdsa_1, alice_ecdsa_2], [bob_ecdsa_1, bob_ecdsa_2], coins, config)

    bob_green_address = GreenAddress(bob_trade, bob_ecdsa_1, bob_ecdsa_2, ecdsa_encrypted, coins, config, address="2N4A41vYSVmQLxnc7EfiAra96FT64UgJFUc", deposit_txid="563e57496c75a3bbc2bf8e29dc12ce5a1c2a55bb98f680e540a3bd301b615427")

    bob_factory = MicrotransferFactory(bob_green_address, coins, config)
    bob = bob_factory.add_contract(bob_trade, [bob_ecdsa_1, bob_ecdsa_2], [alice_ecdsa_1, alice_ecdsa_2], [C("0.00000001"), C("0.00000001")])

    bob_setup = bob_factory.build_setup() 

    #bob = MicrotransferContract(bob_trade, bob_green_address, [bob_ecdsa_1, bob_ecdsa_2], [alice_ecdsa_1, alice_ecdsa_2], coins, config)

    """
    print(alice.our_key_pair)
    print(alice.their_key_pair)
    print("------------")
    print(bob.our_key_pair)
    print(bob.their_key_pair)

    exit()
    """
    #print(alice.our_key_pair["priv"])
    #print(bob.our_key_pair["priv"])
    #exit()


    #CScript([2, x('0369dfed16e87561c4a96ac1c9a023d63d8303ddcc19769cddfe69effdff327ae1'), x('0273af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba034'), x('025098a1d5a338592bf1e015468ec5a8fafc1fc9217feb5cb33597f3613a2165e9'), 3, OP_CHECKMULTISIG]

    print("Alice = " + alice.trade.actor)
    print("Bob = " + bob.trade.actor)
    print("Pair = " + bob.trade.pair[0] + "/" + bob.trade.pair[1])


    """
    print(alice_green_address.currency)
    print(bob_green_address.currency)

    print(alice_green_address.redeem_script())
    print(bob_green_address.redeem_script())

    print()

    print(alice_green_address.ecdsa_1.get_public_key("hex"))
    print(alice_green_address.ecdsa_2.get_public_key("hex"))

    print()

    print(bob_green_address.ecdsa_1.get_public_key("hex"))
    print(bob_green_address.ecdsa_2.get_public_key("hex"))
    """


    """
    alice_setup = alice.build_setup_tx()
    encrypted_sig = alice.sign_setup_tx(alice_setup["tx_hex"], ecdsa_encrypted)
    alice_setup = alice.check_setup_works(alice_setup["tx_hex"], alice_setup["first_sig"], alice_setup["second_sig"], encrypted_sig)

    exit()
    """

    """
b'Signing = 9H&\xbb\x92W\xec\xa4\x8fY\xce\x98\r\x80t\x88{[\xd8\x85!\xe8\xc0\xe5L\xdd}+\xda\x89\x07\x88'
ApeDaYqkbr0IZYwoWb/sjTlPDFh89rAZaQqqC/X8CzA4
b'Pub key = \x02\x97\x83i\x8a\xa4n\xbd\x08e\x8c(Y\xbf\xec\x8d9O\x0cX|\xf6\xb0\x19i\n\xaa\x0b\xf5\xfc\x0b08'
b'Sig = 0D\x02 .&\xd4!\xd3\xd5.w\x81h\xd5\x87\xb7Pn\xe0\xca\xfc\x8dr\xd6\xbc\xae^\x06\xc1\xd0\xe2R\xcd\t\xa0\x02 VX_u\xab\xa4\xd6\xd9\x19r\xd2\x86\xc1\x00\xcc\xe3\xfbs\xed`*f\xeam\x93x[N\xee\xcc\x8b\xbe\x01'

b'Signing = 9H&\xbb\x92W\xec\xa4\x8fY\xce\x98\r\x80t\x88{[\xd8\x85!\xe8\xc0\xe5L\xdd}+\xda\x89\x07\x88'
Aq3GnzfUdHq2C94tKrWeerXlhDIG+zCqRUB9qHo9k6N6
b'Pub key = \x02\xad\xc6\x9f7\xd4tz\xb6\x0b\xde-*\xb5\x9ez\xb5\xe5\x842\x06\xfb0\xaaE@}\xa8z=\x93\xa3z'
b'Sig = 0E\x02!\x00\xc5(f\xf6\x99G)\x00\x18(\xe1\x93\xae\xc48\xe2\x08w\x80.L\x08\xd3\xae\xac\xe5\x89:\x1d\x80\xaf\xa9\x02 Hi\xac\xc9\xf3E\x807\xff<\xae\x8e\x82\x8e)\x88\rM\x9fM\xe2\x17\xcd\xa0\xfa\x00\xcd\xde\xe9Du\xed\x01'
    """
   

    """
    bob_setup = bob.build_setup_tx()

    key = bitcoin.core.key.CECKey()
    pubkey = b'\x02\xad\xc6\x9f7\xd4tz\xb6\x0b\xde-*\xb5\x9ez\xb5\xe5\x842\x06\xfb0\xaaE@}\xa8z=\x93\xa3z'
    sig = b'0E\x02!\x00\xc5(f\xf6\x99G)\x00\x18(\xe1\x93\xae\xc48\xe2\x08w\x80.L\x08\xd3\xae\xac\xe5\x89:\x1d\x80\xaf\xa9\x02 Hi\xac\xc9\xf3E\x807\xff<\xae\x8e\x82\x8e)\x88\rM\x9fM\xe2\x17\xcd\xa0\xfa\x00\xcd\xde\xe9Du\xed\x01'

    pubkey = b'\x02\x97\x83i\x8a\xa4n\xbd\x08e\x8c(Y\xbf\xec\x8d9O\x0cX|\xf6\xb0\x19i\n\xaa\x0b\xf5\xfc\x0b08'
    sig = b'0D\x02 .&\xd4!\xd3\xd5.w\x81h\xd5\x87\xb7Pn\xe0\xca\xfc\x8dr\xd6\xbc\xae^\x06\xc1\xd0\xe2R\xcd\t\xa0\x02 VX_u\xab\xa4\xd6\xd9\x19r\xd2\x86\xc1\x00\xcc\xe3\xfbs\xed`*f\xeam\x93x[N\xee\xcc\x8b\xbe\x01'


    sighash = b'9H&\xbb\x92W\xec\xa4\x8fY\xce\x98\r\x80t\x88{[\xd8\x85!\xe8\xc0\xe5L\xdd}+\xda\x89\x07\x88'

    #sig = base64.b64decode(bob_ecdsa_1.sign(sighash))

    key.set_pubkey(pubkey)
    print(key.verify(sighash, sig))
    print(bob_ecdsa_1.valid_signature(sig, sighash))

    sighash = "test"
    print(sighash)
    sig = base64.b64decode(bob_ecdsa_1.sign(sighash))
    print(b"Second sig = " + sig)

    print(key.verify(sighash, sig))
    print(bob_ecdsa_1.valid_signature(sig, sighash))

    exit()


    sig = b'0E\x02!\x00\xab\xaa&a\xe9\x81\xd8Kr\x8eE\xaa\x03\x14\xa3\xd8\xe6XHy\x8a\xbe%\xb8\x00\x8b\x88\x9a\x03paX\x02 \x15e\xd4I\xda#,\x89\x84\x0f\xdb\x15\x95\xbe\xa1\x86\xa1t\x15\xd1\x02\x00\xd6\xd9o\x06:\x15\xd8\x86]l\x01'


    #print(bob_ecdsa_1.valid_signature(sig, sighash))

    bob_setup["first_sig"] = base64.b64decode(bob_ecdsa_1.sign(sighash))
    print(bob_setup["first_sig"])



    encrypted_sig = bob.sign_setup_tx(bob_setup["tx_hex"], ecdsa_encrypted)
    bob_setup = bob.check_setup_works(bob_setup["tx_hex"], bob_setup["first_sig"], bob_setup["second_sig"], encrypted_sig)

    exit()
    """

    encrypted_sig = sign_setup_tx(bob_setup["tx_hex"], bob_factory.green_address.redeem_script, ecdsa_encrypted)
    bob_setup = check_setup_works(bob_setup["tx_hex"], bob_factory.green_address.redeem_script, bob_setup["first_sig"], bob_setup["second_sig"], encrypted_sig)


    print("setup = ")
    print(bob_setup)

    bob_refund = bob.build_refund_tx(bob_setup["txid"])
    print("refund = ")
    print(bob_refund)



    alice_sig_1 = alice.sign_refund_tx(bob_refund["tx_hex"], 1, "them")
    bob_sig_1 = bob.sign_refund_tx(bob_refund["tx_hex"], 1)
    bob_sig_2 = bob.sign_refund_tx(bob_refund["tx_hex"], 2)




    print("alice sig = ")
    print(alice_sig_1)
    
    print("bob sig = ")
    print(bob_sig_1)

    bob_refund_works = bob.check_refund_works(bob_refund["tx_hex"], bob_sig_1, bob_sig_2, alice_sig_1, "us")




    bob.set_refund(bob_refund["tx_hex"], bob_sig_1, bob_sig_2, alice_sig_1)



    encrypted_sig = sign_setup_tx(alice_setup["tx_hex"], alice_factory.green_address.redeem_script, ecdsa_encrypted)
    alice_setup = check_setup_works(alice_setup["tx_hex"], alice_factory.green_address.redeem_script, alice_setup["first_sig"], alice_setup["second_sig"], encrypted_sig)



    alice_refund = alice.build_refund_tx(alice_setup["txid"])
    bob_sig_1 = bob.sign_refund_tx(alice_refund["tx_hex"], 1, "them")
    alice_sig_1 = alice.sign_refund_tx(alice_refund["tx_hex"], 1)
    alice_sig_2 = alice.sign_refund_tx(alice_refund["tx_hex"], 2)

    alice_refund_works = alice.check_refund_works(alice_refund["tx_hex"], alice_sig_1, alice_sig_2, bob_sig_1, "us")


    #0 | txid, tx_hex (signed)
    alice.set_refund(alice_refund["tx_hex"], alice_sig_1, alice_sig_2, bob_sig_1)

    #def adjust_refund_tx(self, our_bond_txid, their_bond_tx_hex, their_refund_tx_hex, received_tx_hex=None, their_sig=None):
    #tx = CTransaction.deserialize(binascii.unhexlify(ret["tx_hex"]))
    #print(tx)
    #0.00049944
    #print(bob.upload_amount)
    #print(alice.download_amount)

    #print(bob.download_amount)
    #print(alice.upload_amount)

    #print(alice.calculate_chunk_size(alice.download_amount))

    #Alice = seller
    #Bob = buyer
    #Pair = ltc/btc
    #0.01 ltc
    #0.05 btc


    print("")
    print("")

    ret = bob.adjust_refund_tx(bob_setup["txid"], alice_setup["tx_hex"], alice_refund["tx_hex"])
    print("Bob sent: " + str(bob.trade.sent))
    print("Bob recv: " + str(bob.trade.recv))
    print("Bob remaining: " + str(bob.download_amount - bob.trade.recv))


    ret = alice.adjust_refund_tx(alice_setup["txid"], bob_setup["tx_hex"], bob_refund["tx_hex"], ret["tx_hex"], ret["first_sig"], ret["second_sig"])
    
    
    print(ret)
    print("Alice sent: " + str(alice.trade.sent))
    print("Alice recv: " + str(alice.trade.recv))
    print("Alice remaining: " + str(alice.download_amount - alice.trade.recv))

    print(bob_setup)
    print(alice_setup)
    print(alice_refund)
    print(ret)




    ret = bob.adjust_refund_tx(bob_setup["txid"], alice_setup["tx_hex"], alice_refund["tx_hex"], ret["tx_hex"], ret["first_sig"], ret["second_sig"])
    print(ret)
    print("Bob sent: " + str(bob.trade.sent))
    print("Bob recv: " + str(bob.trade.recv))
    print("Bob remaining: " + str(bob.download_amount - bob.trade.recv))
    print("Bob download amount: " + str(bob.download_amount))
    print("Bob upload amount: " + str(bob.upload_amount))


    ret = alice.adjust_refund_tx(alice_setup["txid"], bob_setup["tx_hex"], bob_refund["tx_hex"], ret["tx_hex"], ret["first_sig"], ret["second_sig"])
    print(ret)
    print("Alice sent: " + str(alice.trade.sent))
    print("Alice recv: " + str(alice.trade.recv))
    print("Alice remaining: " + str(alice.download_amount - alice.trade.recv))
    print("Alice download amount: " + str(alice.download_amount))
    print("Alice upload amount: " + str(alice.upload_amount))

    exit()




    #Pass Bob's sig back to Alice.
    #alice.adjust_microtransfer_tx(None, their_sig=sig_bob)


    #setup_bob = bob.build_bond_tx()
    #sig_alice = alice.adjust_microtransfer_tx(bond_bob)["sig"]



    #print(y.adjust_microtransfer_tx("70a7d5e310bd8ee0a2efe7fddaab568f2a71983b1b46b2ca04fb22f124e59e6c", "01000000016c9ee524f122fb04cab2461b3b98712a8f56abdafde7efa2e08ebd10e3d5a7700000000000ffffffff0350c30000000000001976a914c0522c4041dff98ba1d61b43c8fd7fa8af3fd7ef88ac8778f202000000001976a9146a9ea9ed707c22d0812cd67afdeb61019de187fe88ac20a10700000000001976a91405733152fb4d95927a7c7c1bfcc8ada275a4038288ac00000000"))

    #print(y.adjust_microtransfer_tx("01000000016c9ee524f122fb04cab2461b3b98712a8f56abdafde7efa2e08ebd10e3d5a7700000000000ffffffff0350c30000000000001976a914c0522c4041dff98ba1d61b43c8fd7fa8af3fd7ef88ac8778f202000000001976a9146a9ea9ed707c22d0812cd67afdeb61019de187fe88ac20a10700000000001976a91405733152fb4d95927a7c7c1bfcc8ada275a4038288ac00000000"))


    #unsigned_tx_hex
    #print(y.adjust_microtransfer_tx("70a7d5e310bd8ee0a2efe7fddaab568f2a71983b1b46b2ca04fb22f124e59e6c"))
        



    """
    x = 83d26a42f86c039f351c97619d01b0156f0a31aee3202a041b376826d6a4513b
    y = 70a7d5e310bd8ee0a2efe7fddaab568f2a71983b1b46b2ca04fb22f124e59e6c


    tx = x.build_bond_tx()
    print(tx)
    print("-----------")
    print(coins["litecoin"]["rpc"]["sock"].decoderawtransaction(tx))

            redeem_script_hash160 = self.hash160_script(redeem_script)
            txin_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])
    #print(x.build_bond_tx())

    print("sdfsdfsdf")
    """


    """
    x = CScript(x("21029a687cfe735739004781dac6fe7c4c5d4ba846cea032ede0d6bdd9a75d45fe14ac"))
    for op in x:
        print(op)

    print(x)


    print(x.is_p2sh())
    """

    """
    83d26a42f86c039f351c97619d01b0156f0a31aee3202a041b376826d6a4513b
    """





    """
    chunk_size = 
        if exchange rate empty:
            chunk_size = 0.01%
        else:
            

    collateral = 0.001% fee 


    def adjust_microtransfer_tx(self,  



    Create refund transaction from bond amount
    * 1 input to ourselves with the majority of the amount
    * 1 input to who we're transfering the money to
    * 1 input to the fee amount

            txouts.append(CTxOut((send_amount - decimal.Decimal(self.config["mining_fee"]["standard"])) * COIN, p2sh_script_pub_key))
            if change > decimal.Decimal("0"):
                change_seckey = CBitcoinSecret(self.details["bond_change"]["priv"]["wif"])
                change_script_pub_key = CScript([OP_DUP, OP_HASH160, Hash160(change_seckey.pub), OP_EQUALVERIFY, OP_CHECKSIG])
                txouts.append(CTxOut(change * COIN, change_script_pub_key))




    """


