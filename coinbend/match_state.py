
from .globals import *
from .trade_type import *
from .microtransfer_contract import find_microtransfer 
import time

class MatchState:
    def __init__(self, match_sent, match_reply, order=None):
        self.state = None
        self.checked_state = None
        self.state_updated = None

        """
        Used for sending private messages to the node you're trying
        to trade with.
        """
        self.nacl_public_key = None

        """
        The match that you're sending in response to an open
        order in the order book.
        """
        self.match_sent = match_sent

        """
        From the perspective of the node who opened the order, the
        sent match is the reply.
        """
        self.match_reply = match_reply

        """
        This is the order in the order book that a match was sent in response to and its used to reverse a match before recalibrating the match with what is currently available and also just as a general reference.
        """
        self.order = order

        """
        This is a formatted message detailing what is to be traded.
        It can be calculated when sent and reply aren't None.
        """
        self.contract = None
        self.contract_hash = None

        """
        These are handshake messages signing the above contract.
        """
        self.our_handshake_msg = None
        self.their_handshake_msg = None

        """
        After the calibrated match has been generated (what actually remains in accordance with the original request) the quantities for both sides are calculated and stored in to_send and to_recv relative to what they originally requested. It is these values which the contract uses.
        """
        self.to_send = None
        self.to_recv = None

        """
        Store a reference to the direct connection used to create this match.
        """
        self.con = None

        #Update states.
        if self.match_sent == None and self.match_reply == None:
            raise Exception("Invalid matches in match state.")

    def state_machine(self, state):
        valid_states = [
            "pending_calibration",
            "pending_handshake",
            "pending_contract",
            "pending_get_refund_sig",
            "pending_get_setup_tx",
            "pending_microtransfer"
        ]

        if state == self.state:
            return 1

        if state == "pending_calibration":
            if self.state == None:
                return 1

        if state == "pending_handshake":
            if self.state == None:
                return 1

            if self.state == "pending_calibration":
                return 1

        if state == "pending_contract":
            if self.state == "pending_handshake":
                return 1

        if state == "pending_buyer_setup_tx_confirm":
            if self.state == "pending_contract":
                return 1

        if state == "pending_buyer_return_refund_sig":
            if self.state == "pending_contract":
                return 1

            if self.state == "pending_buyer_setup_tx_confirm":
                return 1

        if state == "pending_seller_get_refund_sig":
            if self.state == "pending_contract":
                return 1

        if state == "seller_sent_get_refund_sig":
            if self.state == "pending_seller_get_refund_sig":
                return 1

        if state == "pending_buyer_get_refund_sig":
            if self.state == "pending_buyer_return_refund_sig":
                return 1

        if state == "buyer_sent_get_refund_sig":
            if self.state == "pending_buyer_get_refund_sig":
                return 1

        if state == "pending_seller_return_refund_sig":
            if self.state == "seller_sent_get_refund_sig":
                return 1
        
        if state == "pending_seller_get_setup_tx":
            if self.state == "pending_seller_return_refund_sig":
                return 1

        if state == "seller_sent_get_setup_tx":
            if self.state == "pending_seller_get_setup_tx":
                return 1

        if state == "pending_buyer_return_setup_tx":
            if self.state == "buyer_sent_get_refund_sig":
                return 1

        if state == "pending_buyer_get_setup_tx":
            if self.state == "pending_buyer_return_setup_tx":
                return 1

        if state == "buyer_sent_get_setup_tx":
            if self.state == "pending_buyer_get_setup_tx":
                return 1

        if state == "pending_seller_return_setup_tx":
            if self.state == "seller_sent_get_setup_tx":
                return 1

        if state == "seller_initiate_microtransfer":
            if self.state == "pending_seller_return_setup_tx":
                return 1

        if state == "buyer_accept_microtransfer":
            if self.state == "buyer_sent_get_setup_tx":
                return 1

        if state == "seller_accept_microtransfer":
            if self.state == "seller_initiate_microtransfer":
                return 1

        if state == "pending_microtransfer_complete":
            if self.state == "buyer_accept_microtransfer":
                return 1

            if self.state == "seller_accept_microtransfer":
                return 1

        if state == "pending_microtransfer_confirm":
            if self.state == "pending_microtransfer_complete":
                return 1

        if state == "microtransfer_complete":
            if self.state == "pending_microtransfer_confirm":
                return 1

            if self.state == "pending_microtransfer_complete":
                return 1

        return 0

    def update_state(self, state):
        global trade_engine
        if self.state_machine(state):
            self.state = state
            self.state_updated = time.time()
            if self.contract_hash != None:
                ret = find_microtransfer(self.contract_hash, trade_engine.trades)
                if ret != None:
                    print("Updating microtransfer state with + " + str(state))
                    ret.update(self.state)
                else:
                    print("unable to find microtransfer.")
            else:
                print("Contract hash was not set for update state.")

            return 1

        return 0

    def calibrate_trades(self):
        if self.match_sent == None or self.match_reply == None:
            return 0

        #Extract calibrated trade details.
        if self.match_sent.timestamp > self.match_reply.timestamp:
            #Use match_sent as the calibrated trade template.
            self.to_send = Trade(self.match_sent.trade.action,
            self.match_sent.trade.amount,
            self.match_sent.trade.pair,
            self.match_sent.trade.ppc,
            self.match_sent.trade.order_hash)

            self.to_recv = Trade(self.match_reply.trade.action,
            self.match_sent.trade.amount,
            self.match_sent.trade.pair,
            self.match_sent.trade.ppc,
            self.match_reply.trade.order_hash)
        else:
            #Use match_reply as the calibrated trade template.
            self.to_send = Trade(self.match_sent.trade.action,
            self.match_reply.trade.amount,
            self.match_reply.trade.pair,
            self.match_reply.trade.ppc,
            self.match_sent.trade.order_hash)

            self.to_recv = Trade(self.match_reply.trade.action,
            self.match_reply.trade.amount,
            self.match_reply.trade.pair,
            self.match_reply.trade.ppc,
            self.match_reply.trade.order_hash)

        return 1
