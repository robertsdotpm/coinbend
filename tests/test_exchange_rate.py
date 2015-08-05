from unittest import TestCase
from decimal import Decimal
from coinbend.exchange_rate import *

class test_database(TestCase):
    def test_000000_crypto_pair_order(self):
        exchange = ExchangeRate(0)
        btc_usd = Decimal("355")
        exchange.btc_value = btc_usd
        for handler in exchange.crypto_handlers:
            ret = handler("DOGE", "USD")
            doge_usd = ret["rate"]
            if doge_usd != None:
                if doge_usd != 0:
                    if btc_usd / doge_usd < 1000:
                        error = str(handler) + " returns pair in wrong order."
                        raise Exception(error)

    def test_000001_calculate_rate_logic():
        exchange = ExchangeRate(preload=0, caching=0)
        btc_usd = Decimal("355")
        exchange.btc_value = btc_usd
        crypto_handlers = exchange.crypto_handlers[:]
        #Test crypto / fiat.
        for handler in crypto_handlers:
            exchange.crypto_handlers = [handler]
            rate = exchange.calculate_rate("DOGE", "USD", blocking=1)
            if btc_usd / rate > 1000:
                error = str(handler) + " calculate rate logic for crypto / fiat."
                raise Exception(error)

        #Test crypto / crypto.
        for handler in crypto_handlers:
            exchange.crypto_handlers = [handler]
            rate = exchange.calculate_rate("BTC", "DOGE", blocking=1)
            if rate < 1000:
                error = str(handler) + " calculate rate logic for crypto / crypto."
                raise Exception(error)


"""
#print(ExchangeRate().yahoo("usd", "aud"))
#print(ExchangeRate().google("usd", "aud"))
#print(ExchangeRate().cryptsy("doge", "usd"))
#print(ExchangeRate().vircurex("doge", "usd"))
#print(ExchangeRate().coinmarketcap("doge", "usd"))
#print(ExchangeRate().coins_e("doge", "usd", Decimal(385.00)))
#print(ExchangeRate().cryptocoincharts("doge", "usd", Decimal(385.00)))
#n = [Decimal("0.0002743200000072"), Decimal("0.0003912082825952"), Decimal("0.000267"), Decimal("0.00026180"), Decimal("0.00026180")]

#print(ExchangeRate().cryptocoincharts("btc", "usd"))
#print(ExchangeRate().coinmarketcap("btc", "usd"))
#print(ExchangeRate().cryptsy("btc", "usd"))
#print(ExchangeRate().coins_e("btc", "usd"))
#print(ExchangeRate().vircurex("btc", "usd"))
#print(ExchangeRate().google("btc", "usd"))
#print(ExchangeRate().openexchangerates("btc", "usd"))

#print(ExchangeRate().calculate_rate("aud", "aud")) #1
#print(ExchangeRate().calculate_rate("aud", "usd")) #0.8794323550760968
#print(ExchangeRate().calculate_rate("usd", "aud")) #1.137141750000000
#print(ExchangeRate().calculate_rate("btc", "usd")) #355.50693244
#print(ExchangeRate().calculate_rate("btc", "aud")) #405
#print(ExchangeRate().calculate_rate("btc", "ltc")) #0.01038852004628264
#print(ExchangeRate().calculate_rate("usd", "btc")) #0.002800709395043522
#print(ExchangeRate().calculate_rate("aud", "btc")) #0.002461696585601390
#print(ExchangeRate().calculate_rate("btc", "ltc")) #96.27027335020382
#print(ExchangeRate().calculate_rate("ltc", "btc")) #0.01038852004628264
#print(ExchangeRate().calculate_rate("ltc", "usd")) #3.706246274295782
#print(ExchangeRate().calculate_rate("doge", "aud")) #0.0002872368768968591
#print(ExchangeRate().pair("BTC", "EUR"))
#print(ExchangeRate().pair("DOGE", "USD"))
#Todo implement dustcoin and www.coinpayments.net lookup

#x = time.time()
#e = ExchangeRate()
#print(time.time() - x)
#print()
#print(e.calculate_rate("ltc", "usd"))
#print(e.calculate_rate("usd", "ltc"))
#print(e.calculate_rate("btc", "ltc"))
#print(e.calculate_rate("ltc", "btc"))
#host = "online.wsj.com"
#url = "http://205.203.140.65/mdc/public/page/2_3020-worlddollar.html"
#e.get(url, host)
#print(time.time() - x)
#print(e.bloomberg("aud", "usd"))


#print("yes")
#exit()
#print(e.bter("btc", "usd")["rate"])
#print(e.bittrex("ltc", "usd")["rate"])
#print(e.bter("ltc", "usd")["rate"])
#print(e.coinmarketcap("ltc", "usd")["rate"])
#print(e.dustcoin("ltc", "usd")["rate"])

#print(e.bter("ltc", "usd")["rate"])
#print(e.bittrex("ltc", "usd")["rate"])
#print(e.vircurex("ltc", "usd")["rate"])
#print(e.cryptsy("ltc", "usd")["rate"])
#print(e.xe("ltc", "usd")["rate"])
#print(e.cryptocoincharts("ltc", "usd")["rate"])
#print(e.coins_e("ltc", "usd")["rate"])
#print(e.coinmarketcap("ltc", "usd")["rate"])
#host = "coinpal.net"
#url = "http://199.83.131.68/"
#e.get(url, host)
#print(e.vircurex("doge", "usd"))

#Fiat timeout 2 -- avg ~ 1.5s, min = 0.7
#Lowest fiat exchange rate = google at ~0.47

#cryptocoincharts - 6.241075277328491.........
#cryptsy takes 5 seconds!
#coinmarketcap takes 4.9 seconds!
#vircurex ~1 - 2.3 seconds
#coins-e ~2.6 - 2.8 seconds....

#bittrex "http://162.159.245.225/Markets/Pub_GetMarketSummaries" 0.899
#bter.com 0.9587
#"dustcoin.com" 0.911
#www.coinpayments.net 0.5


#"www.coinwarz.com" 4.3 - 5.5
#https://www.cryptonator.com/rates 7.187628746032715
#https://crypto-trade.com/ 6.69
#"http://104.28.9.96/markets/" 2.1
#poloniex.com 2.49232816696167 - 3
#askcoin.net 3.39
#coin-swap.net 2.8
#coinpal.net 1.611631155014038


#Poloniex

"""

