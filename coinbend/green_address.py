"""
(This is mostly out of date. Will write proper module overviews in the future.)

A green address is defined as any address which can be proven not to be under the total control of the user by giving away some of their leverage to a trusted service in a special multi-sig address [4]. The reason green addresses are required is to address the double-spend problem which exists prior to committing funds for a contract. The idea is that all users are required to commit their funds to a green address before they are allowed to open a contract. In this way, there is no way for them to trick other users into (temporarily) locking their funds into a contract which the attacker can then pull out of, thereby wasting their time through mediation / contract expiry (since the contract bonds are verified by a server and they don't have full control of the green address.)

The explain how green addresses are secure, consider its structure:
    (3 of 4 multisig address [6])
        owner_pub_key_1
        owner_pub_key_2
        server_encrypted_key
        offline_key

The owner creating the green address owns both owner keys. The effect of this means that if the server is ever hacked or the offline key [7] is stolen, the attacker still doesn't have enough pieces to be able to move the money (since 3 keys are required - he can only gain 2 if the owner protects their keys properly.) On the other hand, to ensure the owner's money isn't locked forever the offline key has a special  property: it is time-locked [1]. The ECDSA private key for the offline key is encrypted using a PGP key pair whose private key has been time locked for lets say: 1 year. The details for this are then publicly available, including the IV vector to reconstruct the PGP private key and the ciphertext for the offline_key's private key.

This means that after enough time has passed (hashing multiple times) the PGP key will be cracked, allowing anyone to decrypt the offline_key. The benefit of this is, if anything ever happens to the service and the keys can't be accessed - the owner has assurance that their money won't be inaccessible. For added protection, the IV used to generate the time-locked PGP key will include a timestamp with the most recent news headlines at the time. This should help establish when the time-locked key should be considered insecure as well as ensure the key hasn't already been cracked when its published. The results are also ECDSA signed by the generator as their signature that the IV corresponds to the PGP key.

The last part is the encrypted server key. In its most basic form, the encrypted_server_key is generated uniquely for each green address by a trusted computing component [3] connected to the server whose restrictiveness and physical separation ensure its hard drive and memory contents remain inaccessible even if the full server is owned. The basic scheme for this, involves the encrypted key being encrypted with the trusted component's public key and then stored on the server. To avoid having a single point of failure after a hack, the private key could be split into multiple pieces and a XOR-based one-time pad could be used as a basic shared secret scheme, with the pieces encrypted with individual mediator keys and then encrypted again with the trusted key. (A better solution would involve using threshold ECDSA-signing [0].) For added security, the owner can be a part of the key distribution process for generating the encrypted key, that way if all the mediators are hacked, the owner can make their attempts to recover the key impossible.

Keep in mind, the encrypted server key is suppose to be accessible when it is needed and constructable based on agreement by one or more servers. In conclusion green addresses are secure, temporary holding facilities for funds prior to contract creation.

Technical limitations (part 1) - p2sh restrictions

From a technical perspective, what is required for a green address (and for contracts later on) isn't strictly a standard multi-sig address. What is needed is the ability to be able to specify redemption of a TX from either (owner and encrypted_server) OR (owner and offline.) One way to do this is to use p2sh [8][9] with Bitcoin-style Script code to write a redeem script supporting the above conditions. Unfortunately, if you were to use this approach the transaction would likely be considered non-standard by the majority of miners (who may not have upgraded or merged 7f3b4e95695d50a4970e6eb91faa956ab276f161 which relaxes the rules for IsStandard on p2sh transactions [11] [13] - a very significant development in the Bitcoin world.) 

It turns out the answer lies in a non-obvious combination of keys for normal p2sh multi-sig transactions. The multi-sig is structured to give the owner more leverage over the transaction by doubling their keys in the multi-sig, adding the encrypted_server_key and offline_key as single keys and using 3 of 4. This is already at the limit for number of pub keys in a p2sh TX if the keys are uncompressed [10] (the software uses compressed keys) however to greatly increase the number of keys per TX (useful for contracts) is to use threshold ECDSA signing [0] which allows multiple users to jointly control one ECDSA key.

    (3 of 4 multisig address [6])
        owner_pub_key_1
        owner_pub_key_2
        server_encrypted_key
        offline_key

owner_pub_key_1 + owner_pub_key_2 + server_encrypted key
(owner AND server)

owner_pub_key_1 + owner_pub_key_2 + offline_key
(owner AND offline)

Which is similar to ((owner AND server) OR (owner AND offline)) WITHOUT
using Script.

The benefits of this approach means that diverse contracts are supported while keeping the transaction standard and well within the defined limits of 520 bytes for p2sh [10] [12] (even if uncompressed keys are used.) By only using standard transactions for contracts, it will be easier to support alt-coins for p2p exchange while ensuring no lengthy delays occur before a transaction is included in a block. Finally, because threshold signing allows multiple keys to be consolidated into one ECDSA key (in a sense), the transaction size can be reduced, saving fees and resource burdens on the network.

Technical limitations (part 2) - Single transactions

The outputs for Bitcoin transactions must be spent in their entirely [14] which has practical implications for spending green addresses. When considering one green address per trade - which may have multiple matches and hence multiple contracts, the most efficent use of the green address would be to designate that multiple contracts were funded at the same time from the same green address since you may have to split outputs across two or more contracts. If matching were not to be done in bulk then a single large output from a green address could be taken up by a comparatively small match leaving it inaccessible for a rough time of min_confirmations * block_mining_time.

It is recommended that bond generation for multiple contracts be split over 1 green address and executed in bulk once the microtransfer part of the protocol has been reached for sufficient coverage of the green address. Further optimisation would involve a scheme to split large inputs over the green address such that each input had an even split of coins with the amount being based on some ideal property observed in outside matches for optimum efficiency. Though these issues have been noted, this is left as a future exercise for later versions. For now, matching will be done slowly to keep things simple.

References:
[0] http://www.cs.princeton.edu/~stevenag/bitcoin_threshold_signatures.pdf
[1] http://www.gwern.net/Self-decrypting%20files
[3] http://www.raspberrypi.org/
[4] https://en.bitcoin.it/wiki/Green_address
[5] http://en.wikipedia.org/wiki/Secret_sharing#t_.3D_n
[6] https://en.bitcoin.it/wiki/Script (see OP_CHECKMULTISIG)
[7] https://en.bitcoin.it/wiki/Cold_storage
[8] https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki
[9] https://en.bitcoin.it/wiki/Transaction#Pay-to-Script-Hash
[10] http://bitcoin.stackexchange.com/questions/23893/what-are-the-limits-of-m-and-n-in-m-of-n-multisig-addresses
[11] https://gist.github.com/gavinandresen/88be40c141bc67acb247
[12] https://bitcointalk.org/index.php?topic=585639.20
[13] https://github.com/gavinandresen/bitcoin-git/commit/7f3b4e95695d50a4970e6eb91faa956ab276f161
[14] https://en.bitcoin.it/wiki/Change
"""

from .address import *
from .ecdsa_crypt import *
from .trade_type import *
from .currency_type import *
from .coinlib import *
from decimal import Decimal
import binascii
import copy

def green_redeem_script(ecdsa_1, ecdsa_2, ecdsa_encrypted, ecdsa_offline):
    script = CScript([
        3,
        ecdsa_1.get_public_key("bin"),
        ecdsa_2.get_public_key("bin"),
        ecdsa_encrypted.get_public_key("bin"),
        ecdsa_offline.get_public_key("bin"),
        4,
        OP_CHECKMULTISIG,
    ])

    return {
        "bin": script,
        "hex": binascii.hexlify(script).decode("ascii")
    }

class GreenAddress():
    def __init__(self, trade, ecdsa_1, ecdsa_2, ecdsa_encrypted, coins, config, address=None, deposit_txid=None, use_rpc=1, id=0):
        """
        The trade is copied because object references are passed by value in Python, and we don't want to refer to the same object (since it will be modified later on to remove the trade fees that may be applied to it and this would make subsequent math incorrect.)

        You can think of a green address as a temporary clearing house for all the money that needs to be held in accordance with the trade. It needs to have room for the trade fees so this is added back to trade.amount when remove_fees is called and then the green_address is initialised with the full amount (enough room for any fees.)
        """
        self.trade = trade.copy()
        self.trade.remove_fees()

        #Save other args.
        self.ecdsa_1 = ecdsa_1
        self.ecdsa_2 = ecdsa_2
        self.coins = coins
        self.config = config
        self.currency = self.trade.to_send.currency
        self.tx_fee = self.coins[self.currency]["tx_fee"]
        self.address = address
        self.inputs = []
        self.deposit_txid = deposit_txid
        self.deposit_tx_hex = None
        self.setup_txid = ""
        self.setup_tx_hex = ""
        self.use_rpc = use_rpc
        self.rpc = None
        self.id = id

        """
        These are just placeholders. The code to generate the
        encrypted_key and offline_key has yet to be created.
        """
        self.ecdsa_encrypted = ecdsa_encrypted
        self.ecdsa_offline = ECDSACrypt(self.config["green_address_server"]["offline_key_pair"]["pub"], self.config["green_address_server"]["offline_key_pair"]["priv"])
        self.redeem_script = green_redeem_script(self.ecdsa_1, self.ecdsa_2, self.ecdsa_encrypted, self.ecdsa_offline)

        if self.use_rpc:
            #Set RPC handle for currency
            self.rpc = self.coins[self.currency]["rpc"]["sock"]

            #Calculate p2sh address.
            if self.address == None:
                self.address = self.calculate_address()

            #Deposit funds into green address.
            if self.deposit_txid == None:
                self.deposit_txid = self.deposit()
            else:
                self.deposit_tx_hex = self.rpc.getrawtransaction(self.deposit_txid)

            #Decompose TX address inputs.
            self.load_inputs()

    def save(self):
        with Transaction() as tx:
            sql = "INSERT INTO `green_addresses` (`deposit_txid`, `currency`, `deposit_address`, `deposit_tx_hex`) VALUES (?, ?, ?, ?)"
            tx.execute(sql, (self.deposit_txid, self.currency, self.address, self.deposit_tx_hex))
            self.id = tx.db.cur.lastrowid

        for ecdsa in [self.ecdsa_1, self.ecdsa_2]:
            ecdsa.save()

    def update(self):
        with Transaction() as tx:
            sql = "UPDATE `green_addresses` SET `setup_txid`=?,`setup_tx_hex`=?,`deposit_txid`=?,`deposit_tx_hex`=? WHERE `id`=?"
            tx.execute(sql, (self.setup_txid, self.setup_tx_hex, self.deposit_txid, self.deposit_tx_hex, self.id))

    def copy(self):
        return GreenAddress(self.trade.copy(), self.ecdsa_1, self.ecdsa_2, self.ecdsa_encrypted, self.coins, self.config, self.address, self.deposit_txid, self.use_rpc, self.id)

    def calculate_address(self):
        return Address(currency=self.currency, coins=self.coins, is_p2sh=1).construct_address(self.redeem_script["bin"])

    def get_input(self, vout=None):
        if vout == None:
            if len(self.inputs):
                return self.inputs[0]
            else:
                return None

        for tx_input in self.inputs:
            if tx_input["vout"] == vout:
                return tx_input
        
        return None 

    def load_inputs(self):
        #1 == verbose
        self.deposit_tx = self.rpc.getrawtransaction(self.deposit_txid, 1)
        if "confirmations" in self.deposit_tx:
            confirmations = self.deposit_tx["confirmations"]
        else:
            confirmations = 0

        #Record all outputs to the address - ignore anything else that
        #might have been added like change.
        address_found = 0
        for vout in self.deposit_tx["vout"]:
            if vout["scriptPubKey"]["type"] != "scripthash":
                continue

            if vout["scriptPubKey"]["addresses"][0] != self.address:
                continue

            """
            The magic vout - tx_fee is here because an additional tx_fee is added to the deposit amount to serve as the TX fee for the setup transaction. Calculation code doesn't actually see the extra quantity so the TX fees for the setup TX are handled 100% transparently.
            """
            address_found = 1
            jason = {
                "txid": self.deposit_txid,
                "vout": vout["n"],
                "amount": vout["value"] - self.tx_fee.as_decimal,
                "confirmations": confirmations
            }

            #Check unspent.
            tx_out = self.rpc.gettxout(self.deposit_txid, vout["n"])
            if tx_out == None:
                continue

            #Save unspent output.
            self.inputs.append(jason)

        """
        Check whether valid offline key is included. Note that this shouldn't be relied on as a complete security check for whether an address is a green address since the encrypted key still needs to be checked at the server.
        """
        if not address_found:
            raise Exception("Not a valid green address.")

    def deposit(self):
        #Check send amount isn't too low.
        print(self.trade.to_send)
        if self.trade.to_send < (C(2) * self.tx_fee):
            raise Exception("The TX fees for the contract are more than you're trying to send.")

        #Deposit money in green address.
        self.rpc = self.coins[self.currency]["rpc"]["sock"]

        """
        The amount to send is actually amount + standard transaction fee with the difference being hidden by this class. The advantage of this approach means the complexity of having to pay transaction fees for setup transactions (from a green address) can be handled automatically without any attention to handling yet another fee, plus the expected amount to work with from a contract perspective won't have the transaction fees taken away from it (which has to be taken from somewhere and would vastly complicate the overall math and transaction code.)

        (The TX fee for the deposit into the green address is handled automatically by the coin daemond.)
        """
        send_amount = self.trade.to_send + self.tx_fee
        txid = self.rpc.sendtoaddress(self.address, send_amount.as_decimal)
        self.deposit_tx_hex = self.rpc.getrawtransaction(txid)
        return txid

    #Type conversation to str
    def __str__(self):
        return self.address

if __name__ == "__main__":
    trade = Trade("sell", "0.05", ["bitcoin", "litecoin"], "0.5")
    ecdsa_1 = ECDSACrypt()
    ecdsa_2 = ECDSACrypt()
    ecdsa_encrypted = ECDSACrypt()
    green = GreenAddress(trade, ecdsa_1, ecdsa_2, ecdsa_encrypted, coins, config, address="2Mshbgs2d9GhzsjLUz8PYHErLaTzmzJmR6d", deposit_txid="c508268f8960e5e79d9ab8f0eb65d0b1550e660316a236eed0ebe6c57e8e4547")
    print(green.deposit_txid)

