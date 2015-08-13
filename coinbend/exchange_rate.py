# -*- coding: utf-8 -*-

"""
This module is used to calculate the universal exchange rate
between currencies. It works by retrieving results from
multiple external sources and then using a trimmed mean
function to discard outliers before averaging results. It
is hoped this will provide an accurate overview for the
price of a currency used to inform buying on the exchange
by eliminating arbitrage between sources and excluding
the cost of doing business.

Because this is not correct economics, this exchange rate
is currently only used as a guideline to inform users of
a recommended price on the basis that they're investing,
selling mined coins, or obtaining coins because they
need them. A different algorithm will be used for working
out the actual exchange rate on the network and this will
be much more useful for traders. Consider this module
a simple solution to start with.

Notes:
* All rates returned by the cryptocurrency functions are
designed to be quoted in USD.
* The class uses caching to store results as external
exchange rates are subject to network conditions.
* Cached results are updated frequently based on the
average speed to retrieve the results. Results returned
by slow routes are updated less frequently.
* IP addresses are hard coded to avoid the lag of DNS
lookups - this can be a problem if the IP changes so
unit tests will be necessary.
* The class is preinitialised with the price for
USD/BTC, FIAT/USD, and many other crypto pairs. The
initialisation averages 3 seconds and means subsequent
calls can potentially be returned instantly.
* The freshness of the rates isn't ideal for day trading
-- this module is for other users.
* This function doesn't work at all with -erateinit -- the pairs are reversed!    
"""


import re
from decimal import Decimal, getcontext
from bs4 import BeautifulSoup
import json
import time
from threading import Thread, Lock
import copy
from .cryptocurrencies import *
from .fiatcurrencies import *
from .currency_type import *
from .lib import *
import urllib.parse
import urllib.request


class ExchangeRate():
    def __init__(self, config, preload=1, caching=1, btc_value_init=1):
        self.config = config
        self.mutex = Lock()
        self.preload = preload
        self.caching = caching
        self.timeout = 5
        getcontext().prec = C().precision
        self.slow_route_expiry = 30 * 60
        self.fast_route_expiry = 5 * 60
        self.btc_value = Decimal("0")
        self.last_btc_update = None
        self.btc_update_interval = 5 * 60
        self.active_threads = {}
        self.cached_rates = {}
        self.routes = {
            self.bittrex: {
                "type": "crypto",
                "execution": Decimal("0.899"),
                "currencies": []
            },
            self.bter: {
                "type": "crypto",
                "execution": Decimal("1.9587"), #Used to be 0.9 wtf?
                "currencies": []
            },
            self.coinmarketcap: {
                "type": "crypto",
                "execution": Decimal("4.9"),
                "currencies": []
            },
            self.coinpayments: {
                "type": "crypto",
                "execution": Decimal("1.789"),
                "currencies": []
            },
            self.coins_e: {
                "type": "crypto",
                "execution": Decimal("2.7"),
                "currencies": []
            },
            self.cryptocoincharts: {
                "type": "crypto",
                "execution": Decimal("6.2410"),
                "currencies": []
            },
            self.cryptsy: {
                "type": "crypto",
                "execution": Decimal("5"),
                "currencies": []
            },
            self.dustcoin: {
                "type": "crypto",
                "execution": Decimal("0.911"),
                "currencies": []
            },
            self.ecb: {
                "type": "fiat",
                "execution": Decimal("1.70"),
                "currencies": []
            },
            self.google: {
                "type": "fiat",
                "execution": Decimal("0.37463"),
                "currencies": ["BTC"]
            },
            self.openexchangerates: {
                "type": "fiat",
                "execution": Decimal("0.8560"),
                "currencies": []
            },
            self.vircurex: {
                "type": "crypto",
                "execution": Decimal("1.88"),
                "currencies": []
            },
            self.xe: {
                "type": "fiat",
                "execution": Decimal("1.50688624"),
                "currencies": []
            },
            self.yahoo: {
                "type": "fiat",
                "execution": Decimal("1.4450163"),
                "currencies": []
            },
            self.bloomberg: {
                "type": "fiat",
                "execution": Decimal("0.7234"),
                "currencies": []
            }
        }

        #Speed lookups for routes.
        self.crypto_handlers = []
        self.fiat_handlers = []
        for route in list(self.routes):
            if self.routes[route]["type"] == "crypto":
                if self.routes[route]["execution"] <= 1:
                    self.crypto_handlers.append(route)
            else:
                if self.routes[route]["execution"] <= 1:
                    self.fiat_handlers.append(route)

        #This will cause the fastest routes to start first.
        for route in list(self.routes):
            if self.routes[route]["type"] == "crypto":
                if self.routes[route]["execution"] > 1:
                    self.crypto_handlers.append(route)
            else:
                if self.routes[route]["execution"] >1:
                    self.fiat_handlers.append(route)

        #Load self.btc_value.
        if self.btc_value == Decimal("0"):
            if btc_value_init:
                self.load_btc_value()

        #Load USD exchange rates.
        self.threaded_handler(self.bloomberg, "AUD", "USD", 5)
        self.mutex.acquire() #(Block until done.)
        self.mutex.release()

        #Preload rates for faster initial returns.
        if self.preload:
            #Finally, init crypto values by depending on extra results
            #returned by doing a normalized query:
            self.calculate_rate("LTC", "BTC")

    def broken_threaded_handler(self, handler, base, quote, timeout):
        try:
            self.mutex.release()
        except:
            pass

        self.active_threads[handler] = None

    def manual_override(self, exchange_rates):
        #Override handlers.
        self.threaded_handler = self.broken_threaded_handler

        #Update cached results with manual results.
        for exchange_rate in exchange_rates:
            base = exchange_rate[0].upper()
            quote = exchange_rate[1].upper()
            rate = Decimal(exchange_rate[2])

            #Init self.btc_value.
            if base == "BTC" and quote == "USD":
                self.btc_value = rate

            #Spoof results for handler.
            if base not in fiatcurrencies:
                handler = self.bittrex
            else:
                handler = self.google
            
            try:
                #Add new result.
                ret = {
                    "rate": rate,
                    "extra": {}
                }
                self.append_result(ret, handler, base, quote)
                self.mutex.release()
            except Exception as e:
                continue

    def load_btc_value(self):
        current_time = time.time()
        if self.last_btc_update:
            elapsed = int(current_time - self.last_btc_update)
            if elapsed < self.btc_update_interval:
                return

        self.last_btc_update = current_time
        routes = [self.coinbase, self.google, self.yahoo]
        for route in routes:
            try:
                value = route("BTC", "USD")["rate"]
                if not value or value == None:
                    raise Exception("Something went wrong.")
                self.btc_value = value
                return
            except:
                continue

        raise Exception("Unable to load self.btc_value.")

    def append_result(self, ret, handler, base, quote):
        #Put results in extra dict so they're easier to process.
        if ret["rate"]:
            ret["extra"][base + "/" + quote] = ret["rate"]

        #Add flipped pairs to the results.
        rates = self.append_inverted_rates(ret["extra"])

        #Convert X/BTC to X/USD
        #(since mostly everything internal is against USD.)
        usd_rates = {}
        for pair in list(rates):
            currencies = pair.split("/")
            base, quote = currencies
            usd_pair = base + "/USD"
            if usd_pair not in rates and usd_pair != "USD/USD":
                if quote == "BTC" and self.btc_value and rates[pair]:
                    usd_value = rates[pair] * self.btc_value
                    rates[usd_pair] = usd_value
        rates = self.append_inverted_rates(rates)

        #Update cached rates.
        self.mutex.acquire()
        for pair in list(rates):
            #Init.
            if pair not in self.cached_rates:
                self.cached_rates[pair] = {}

            #Non-zero / invalid values are discarded.
            if rates[pair]:
                rate = {
                    "timestamp": time.time(),
                    "value": rates[pair]
                }
                self.cached_rates[pair][handler] = rate 

    def threaded_handler(self, handler, base, quote, timeout):
        try:
            ret = handler(base, quote, timeout)
            self.append_result(ret, handler, base, quote)
        except Exception as e:
            print("Threaded handler error.")
            print(handler)
            print(e)
            pass
        finally:
            #Because the mutex isn't guaranteed to be aquired.
            try:
                self.mutex.release()
            except:
                pass
            self.active_threads[handler] = None

    def append_inverted_rates(self, extra):
        appended = copy.deepcopy(extra)
        for pair in list(extra):
            #Reverse the pair: USD/AUD -> AUD/USD
            inverted = "/".join(list(reversed(pair.split("/"))))
            if inverted not in appended:
                if extra[pair]:
                    value = 1 / extra[pair]
                    if value:
                        appended[inverted] = value
        return appended

    def pair(self, base, quote="USD"):
        return self.calculate_rate(base, quote)

    def currency_converter(self, rate, from_currency, to_currency):
        if from_currency == to_currency:
            return rate

        relative = self.calculate_rate(from_currency, to_currency)
        if relative == 0:
            return Decimal("0")
        return rate / (1 / relative) 

    def calculate_rate(self, base, quote="USD", blocking=0):
        global cryptocurrencies
        global fiatcurrencies

        crypto_handlers = self.crypto_handlers[:]
        fiat_handlers = self.fiat_handlers[:]
        t = time.time()
        base = base.upper()
        quote = quote.upper()
        pair = base + "/" + quote
        rates = []

        #Update btc_value if its old enough.
        self.load_btc_value()

        #No exchange required.
        if base == quote:
            return Decimal("1")

        #Return self.btc_value.
        if base == "BTC" and quote == "USD":
            return self.btc_value

        #Disable caching.
        if not self.caching:
            self.cached_rates = {}

        #Do we know about these currencies?
        for currency in [base, quote]:
            found = 0
            currency = currency.lower()
            for known_currencies in [fiatcurrencies, cryptocurrencies]:
                if currency in known_currencies:
                    found = 1
                    break

            if not found:
                return Decimal(0)

        """
        Remove handlers for rates that haven't expired yet.
        Note that expired rates aren't removed from the
        result set before computing the trimmed mean. This
        is because if they all expire at once before
        computing the new exchange rate it can cause unnatural
        price swings when the average is computed from only a
        subset of results. Instead, the results are replaced over time,
        as they become available, sliding the average and frequent
        updates ensure the rate is always accurate.
        """
        stagnant_rates = []
        if pair in self.cached_rates:
            for handler in list(self.cached_rates[pair]):
                cached_rate = self.cached_rates[pair][handler]
                elapsed = t - cached_rate["timestamp"]
                if self.routes[handler]["execution"] > 1:
                    if elapsed >= self.slow_route_expiry:
                        stagnant_rates.append({"handler": handler, "value": cached_rate["value"]})
                    else:
                        #Not expired - no reason to get it again.
                        if handler in self.crypto_handlers:
                            crypto_handlers.remove(handler)
                        if handler in self.fiat_handlers:
                            fiat_handlers.remove(handler)
                else:
                    if elapsed >= self.fast_route_expiry:
                        stagnant_rates.append({"handler": handler, "value": cached_rate["value"]})
                    else:
                        #Not expired - no reason to get it again.
                        if handler in self.crypto_handlers:
                            crypto_handlers.remove(handler)
                        if handler in self.fiat_handlers:
                            fiat_handlers.remove(handler)

        #Calculate FIAT/Crypto rates form multiple sources.
        if base.lower() in fiatcurrencies and quote.lower() in cryptocurrencies:
            ret = self.calculate_rate(quote, base, blocking)
            if ret == 0:
                return Decimal("0")

            return 1 / ret

        if base.lower() in fiatcurrencies:
            #Calculate FIAT/FIAT rates from multiple sources.
            quote_value = quote
            handlers = fiat_handlers
        else:
            #Calculate CRYPTO/USD exchange rate from multiple sources.
            quote_value = "USD"
            pair = base + "/USD"
            handlers = crypto_handlers

        """
        The meanings behind the code begin to fade. The logic, which at first was as clear as red flame, has all but disappeared - a secret now that only the interpreter can tell.
        """
        if pair == "BTC/USD":
            ret = self.btc_value
        else:
            #Start handlers.
            for handler in handlers:
                if handler in self.active_threads:
                    #Thread already started - avoid starting a million threads.
                    if self.active_threads[handler] != None:
                        continue
                self.active_threads[handler] = Thread(target=self.threaded_handler, args=(handler, base, quote_value, 5))
                self.active_threads[handler].start()
                if blocking:
                    self.active_threads[handler].join()

            #Instead of waiting - try return cached result if there is one.
            elapsed = 0
            if pair in self.cached_rates:
                if len(self.cached_rates[pair]):
                    elapsed = 1337

            #Wait for minimum time to get (some) results.
            if not blocking:
                start = time.time()
                while 1:
                    if elapsed >= 1.5:
                        break
                    if pair in self.cached_rates:
                        if len(self.cached_rates[pair]) >= 5:
                            break
                    time.sleep(0.1)
                    elapsed = time.time() - start
            self.mutex.acquire()
            if pair not in self.cached_rates:
                self.mutex.release()
                return Decimal("0")

            #Calculate rates.
            for handler in list(self.cached_rates[pair]):
                cached_rate = self.cached_rates[pair][handler]
                value = cached_rate["value"]
                if value != None:
                    rates.append(value)

            if not len(rates):
                self.mutex.release()
                return Decimal("0")
            self.mutex.release()

            #Average exchange rate discarding outliers.
            rates_len = len(rates)
            ret = None
            if rates_len == 1:
                ret = rates[0]

            if rates_len == 2:
                if rates[0] < rates[1]:
                    ret = rates[0]
                else:
                    ret = rates[1]

            if rates_len >= 3:
                ret = trimmed_mean(rates)

        #Display exchange rate in correct quote fiat currency.
        if (quote.lower() in fiatcurrencies and quote != "USD" and base.lower() not in fiatcurrencies):
            rate = self.calculate_rate(quote, "USD", blocking)
            if rate != 0:
                ret = ret / rate

        #Display exchange rate in correct quote crypto currency.
        if quote.lower() in cryptocurrencies:
            rate = self.calculate_rate(quote, "USD", blocking)
            if rate != 0:
                ret = ret / rate

        #Catch this error.
        if ret == self.btc_value and (base == "BTC" and quote != "USD"):
            return Decimal(0)

        #Not guaranteed to be acquired.
        return ret
    
    def get(self, url, host=None, timeout=5):
        headers = {'User-Agent': 'Mozilla/5.0'}
        ip_addr = re.findall("https?[:]//([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)", url)
        if len(ip_addr):
            if host != None:
                headers['host'] = host
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req, timeout=timeout).read()
        #response.decode("ISO-8859-1").encode("utf-8")?
        response = response.decode("utf-8")
        return response

    def soupify(self, url, host=None, timeout=5):
        soup = BeautifulSoup(self.get(url, host, timeout))
        return soup

    def ecb(self, base, quote, timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        url = "http://23.10.0.47/stats/exchange/eurofxref/html/index.en.html"
        host = "www.ecb.europa.eu"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        #Get currency rates relative to Euros.
        rows = soup.find("tbody").findAll("tr")
        rates = []
        for row in rows:
            cols = row.findAll("td")
            if len(cols) < 3:
                continue
            code = cols[0].get_text()
            currency = cols[1].get_text()
            value = cols[2].get_text()
            if re.match("\s+", value) != None:
                continue
            
            rate = {
                "code": code.upper(),
                "currency": currency,
                "value": Decimal(value)
            }
            rates.append(rate)

        #Find exchange rate.
        euro_slash_base = 0
        euro_slash_quote = 0
        for rate in rates:
            if rate["code"] == base:
                euro_slash_base = rate["value"]
            if rate["code"] == quote:
                euro_slash_quote = rate["value"]

        while 1:
            if not euro_slash_base and base != "EUR":
                break
            if not euro_slash_quote and quote != "EUR":
                break

            #Calcualte exchange rate using euro as a reference.
            if base == "EUR":
                #EUR/X
                ret["rate"] = Decimal(euro_slash_quote)
            elif quote == "EUR":
                #X/EUR
                ret["rate"] = Decimal(1 / euro_slash_base)
            else:
                """
                X/Y
                Note that this isn't correct economics.
                But fiat exchange rates are normalized against multiple
                sources so it doesn't matter.
                """
                ret["rate"] = Decimal(euro_slash_quote / euro_slash_base)
            break

        #Set extra exchange rates.
        for rate in rates:
            ret["extra"]["EUR/" + rate["code"]] = rate["value"]

        return ret

    def xe(self, base, quote, timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.xe.com"
        url = "http://www.xe.com/currencyconverter/convert/?Amount=1&From=" + base + "&To=" + quote
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rate = soup.find("tr", "uccRes").find("td", "rightCol").get_text()
        rate = re.findall("([0-9]+(?:[.][0-9]+)?)", rate)
        if len(rate):
            if rate[0]:
                ret["rate"] = Decimal(rate[0])

        return ret

    def yahoo(self, base, quote, timeout=8):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "finance.yahoo.com"
        url = "http://finance.yahoo.com/d/quotes.csv?e=.csv&f=sl1d1t1&s=" + base + quote + "=X"
        data = self.get(url, timeout=timeout)
        try:
            ret["rate"] = Decimal(data.split(",")[1])
        except:
            ret["rate"] = None

        return ret

    def google(self, base, quote, timeout=8):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.google.com"
        url = "http://74.125.237.195/finance/converter?a=1&from=" + base + "&to=" + quote
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rate = soup.find("span", "bld").get_text()
        rate = re.findall("([0-9]+(?:[.][0-9]+)?)", rate)
        if len(rate):
            ret["rate"] = Decimal(rate[0])

        return ret

    def openexchangerates(self, base, quote, timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "openexchangerates.org"
        url = "http://185.24.96.251/api/latest.json?app_id=" + self.config["openexchangerates"]["app_id"]
        rates = json.loads(self.get(url, host, timeout))["rates"]

        #Find exchange rates.
        while 1:
            usd_slash_base = 0
            usd_slash_quote = 0
            if base in rates:
                usd_slash_base = rates[base]
            if quote in rates:
                usd_slash_quote = rates[quote]
            if not usd_slash_base and base != "USD":
                break
            if not usd_slash_quote and quote != "USD":
                break

            #Calcualte exchange rate using USD as a reference.
            if base == "USD":
                #USD/X
                ret["rate"] = Decimal(usd_slash_quote)
            elif quote == "USD":
                #X/USD
                ret["rate"] = Decimal("1") / Decimal(usd_slash_base)
            else:
                """
                X/Y
                Note that this isn't correct economics.
                But fiat exchange rates are normalized against multiple
                sources so it doesn't matter.
                """
                ret["rate"] = Decimal(usd_slash_quote) / Decimal(usd_slash_base)
            break

        #Set extra rates.
        for code in list(rates):
            ret["extra"]["USD/" + code.upper()] = Decimal(rates[code])

        return ret

    def cryptsy(self, base, quote="USD", timeout=5):
        """
        Since the alt coins are against Bitcoin,
        we first get the value of Bitcoin against the USD to
        work out the USD price of alt-coins.
        """
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.cryptsy.com"
        url = "http://103.28.250.5/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret
        if not self.btc_value:
            return ret

        rates = {}
        markets = soup.find_all("a", class_=re.compile('leftmarketinfo_[0-9]+'))
        for market in markets:
            try:
                market_pair, value = re.findall("([a-zA-Z0-9]+/[a-z-A-Z0-9]+)(?:\s+)?([0-9]+(?:[.][0-9]+))", market.get_text())[0]
                rates[market_pair] = Decimal(value)
            except:
                continue

        #Get exchange rate.
        while 1:
            if "BTC/USD" not in rates:
                break
            if base == "BTC":
                ret["rate"] = rates["BTC/USD"]
                break
            
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * rates["BTC/USD"]
            break

        #Get extra rates.
        for pair in list(rates):
            ret["extra"][pair.upper()] = rates[pair]

        return ret

    def coinmarketcap(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "coinmarketcap.com"
        url = "http://162.159.240.183/currencies/views/all/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) != 10:
                continue

            try:
                code = re.findall("([a-zA-Z0-9]+)", cols[2].get_text())[0]
                value = re.findall("([0-9]+(?:[.][0-9]+))", cols[4].get_text())[0]
                rates[code] = Decimal(value)
            except:
                continue

        #Set exchange rate.
        if base in rates:
            ret["rate"] = rates[base]

        #Set extra.
        for code in list(rates):
            ret["extra"][code.upper() + "/USD"] = rates[code]
        
        return ret

    def vircurex(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "vircurex.com"
        url = "http://162.159.245.32/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) != 5:
                continue

            try:
                pair = re.findall("([a-zA-Z0-9]+/[a-zA-Z0-9]+)", cols[0].get_text())[0]
                value = re.findall("([0-9]+(?:[.][0-9]+))", cols[3].get_text())[0]
                rates[pair] = Decimal(value)
            except:
                continue


        #Return exchange rate.
        while 1:
            if "BTC/USD" not in rates:
                break
            if base == "BTC":
                ret["rate"] = rates["BTC/USD"]
                break
            
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * rates["BTC/USD"]
            break

        #Extra exchange rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def coins_e(self, base, quote="USD", timeout=8):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.coins-e.com"
        url = "http://www.coins-e.com/data/v2/markets/data/"
        json_result = json.loads(self.get(url, host, timeout))
        markets = json_result["healthy"]
        markets.update(json_result["maintenance"])
        rates = {}
        for market_id in list(markets):
            pair = "/".join(market_id.split("_"))
            rates[pair] = Decimal(markets[market_id]["ltp"])
    
        #Calculate exchange rate.
        while 1:
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * self.btc_value
            break

        #Calculate extra.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def cryptocoincharts(self, base, quote="USD", timeout=10):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.cryptocoincharts.info"
        url = "http://www.cryptocoincharts.info/coins/info"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret
        if not self.btc_value:
            return ret

        units = {
            "µBTC": Decimal("0.000001"),
            "mBTC": Decimal("0.001"),
            "BTC": Decimal("1")
        }
        rates = {}
        rows = soup.find("tbody").find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) != 8:
                continue
            
            try:
                code = re.findall("([^\s]+)", cols[0].get_text())[0]
                unit_pattern = "("
                for unit in list(units):
                    unit_pattern += unit + "|"
                unit_pattern = unit_pattern[:-1] + ")"
                frodo = "([0-9]+(?:[.][0-9]+))\s+" + unit_pattern
                value, unit = re.findall(frodo, cols[4].get_text())[0]
                rates[code] = Decimal(value) * units[unit]
            except:
                continue

        #Calculate exchange rate.
        while 1:
            if base not in rates:
                break

            ret["rate"] = rates[base] * self.btc_value
            break

        #Calculate extra.
        for code in list(rates):
            ret["extra"][code.upper() + "/BTC"] = rates[code]

        return ret

    def bittrex(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.bittrex.com"
        url = "https://www.bittrex.com/api/v2.0/pub/Markets/GetMarketSummaries"
        markets = json.loads(self.get(url, host, timeout))["result"]
        rates = {}
        for market in markets:
            base_currency = market["Market"]["MarketCurrency"].upper()
            quote_currency = market["Market"]["BaseCurrency"].upper()
            pair = base_currency + "/" + quote_currency
            if Decimal(market["Summary"]["Last"]):
                rates[pair] = Decimal(market["Summary"]["Last"])
        
        #Set exchange rate.
        pair = base + "/" + quote
        if pair in rates:
            ret["rate"] = rates[pair]

        #Set extra rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def bter(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "bter.com"
        url = "http://141.101.121.208/marketlist/BTC"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        rows = soup.find("tbody").find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) != 8:
                continue
            
            pair = cols[1].get_text()
            value = re.findall("([0-9]+(?:[.][0-9]+)?)", cols[2].get_text())
            if not len(value):
                continue
            else:
                value = value[0]
            rates[pair] = Decimal(value)

        #Set exchange rate.
        while 1:
            if "BTC/USD" not in rates:
                break
            if base == "BTC":
                ret["rate"] = rates["BTC/USD"]
                break
            
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * rates["BTC/USD"]
            break

        #Set extra rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def dustcoin(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "dustcoin.com"
        url = "http://dustcoin.com/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        rows = soup.find_all("tr", class_=re.compile('coin'))
        for row in rows:
            cols = row.find_all("td")
            if len(cols) != 12:
                continue
            
            currency = cols[0].get_text().lower().strip()
            if currency == "bitcoin":
                continue
            if currency not in cryptocurrencies:
                continue
            value = re.findall("([0-9]+(?:[.][0-9]+)?)", cols[6].get_text())
            if not len(value):
                continue

            pair = cryptocurrencies[currency]["code"].upper() + "/BTC"
            rates[pair] = Decimal(value[0])

        #Set exchange rate.
        while 1:
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * self.btc_value
            break

        #Set extra rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def coinpayments(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.coinpayments.net"
        url = "https://www.coinpayments.net/supported-coins"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        #table = soup.find_all("table", class_=re.compile("table[-]bordered"))[0]
        all_coins = soup.find_all("div", class_=re.compile("single_coins"))
        for row in all_coins:
            cols = row.find_all("p")
            code = row.find_all("a")
            if not len(code):
                continue
            else:
                code = code[0].attrs["name"].upper().strip()

            value = re.findall("([0-9]+(?:[.][0-9]+)?)", cols[4].get_text())
            if not len(value):
                continue

            pair = code + "/BTC"
            rates[pair] = Decimal(value[0])

        #Set exchange rate.
        while 1:
            pair = base + "/BTC"
            if pair not in rates:
                break

            ret["rate"] = rates[pair] * self.btc_value
            break

        #Set extra rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def bloomberg(self, base, quote="USD", timeout=5):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.bloomberg.com"
        url = "http://www.bloomberg.com/markets/currencies/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret

        rates = {}
        tables = soup.find_all("tbody")
        for table in tables:
            rows = soup.find_all("tr")
            for row in rows:
                #Find viable table.
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                #Find USD currency pairs.
                pair = re.findall("(?:(USD|[A-Z]+)[-](USD|[A-Z]+))|(?:([A-Z]+)[-](USD))", cols[0].get_text())
                if not len(pair):
                    continue
                pair = list(filter(None, pair[0]))
                if len(pair) != 2:
                    continue
                pair = "/".join(pair)

                #Extract value.
                value = re.findall("([0-9]+(?:[.][0-9]+)?)", cols[1].get_text())
                if not len(value):
                    continue

                rates[pair] = Decimal(value[0])

        #Set exchange rate.
        while 1:
            pair = base + "/" + quote
            if pair not in rates:
                break

            ret["rate"] = rates[pair]
            break

        #Set extra rates.
        for pair in list(rates):
            ret["extra"][pair] = rates[pair]

        return ret

    def coinbase(self, base, quote, timeout=8):
        ret = {
            "rate": None,
            "extra": {}
        }
        base = base.upper()
        quote = quote.upper()
        host = "www.coinbase.com"
        url = "https://www.coinbase.com/"
        soup = self.soupify(url, host, timeout)
        if soup == None:
            return ret
        
        rate = soup.find_all("li", class_=re.compile('top-balance'))[0]
        rate = rate.findAll("a", {"href" : "/charts"})[0].get_text()
        rate = re.findall("([0-9]+(?:[.][0-9]+)?)\s*$", rate)
        if len(rate):
            ret["rate"] = Decimal(rate[0])

        return ret

"""
Todo finish this
def x_rates(self, base, quote="USD", timeout=5):
    ret = {
        "rate": None,
        "extra": {}
    }
    base = base.upper()
    quote = quote.upper()
    host = "www.x-rates.com"
    url = "http://54.84.44.192/table/?from=USD"
    soup = self.soupify(url, host, timeout)
    if soup == None:
        return ret

    rates = {}
    tables = soup.find_all("table")
    for table in tables:
        rows = soup.find_all("tr")
        for row in rows:
            #Find viable table.
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            #Find USD currency pairs.
            pair = re.findall("(?:(USD|[A-Z]+)[-](USD|[A-Z]+))|(?:([A-Z]+)[-](USD))", cols[0].get_text())
            if not len(pair):
                continue
            pair = list(filter(None, pair[0]))
            if len(pair) != 2:
                continue
            pair = "/".join(pair)

            #Extract value.
            value = re.findall("([0-9]+(?:[.][0-9]+)?)", cols[1].get_text())
            if not len(value):
                continue

            rates[pair] = Decimal(value[0])

    #Set exchange rate.
    while 1:
        pair = base + "/" + quote
        if pair not in rates:
            break

        ret["rate"] = rates[pair]
        break

    #Set extra rates.
    for pair in list(rates):
        ret["extra"][pair] = rates[pair]

    return ret
"""

if __name__ == "__main__":
    """
python3.3 -m "coinbend.exchange_rate" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -29.9615900039672851562500 -skipbootstrap 1 -fastload 1 -skipnet 1 -skipforwarding 1 -externalexchange 0 -coins 0
    """

    #print(e_exchange_rate.currency_converter(Decimal(1), "LTC", "USD"))
    #print(e_exchange_rate.currency_converter(Decimal(0.03), "btc", "usd"))

    """
    time.sleep(20)
    print(e_exchange_rate.calculate_rate("BTC", "NVC"))
    print(e_exchange_rate.calculate_rate("DOGE", "USD"))
    print(e_exchange_rate.calculate_rate("USD", "DOGE"))
    print(e_exchange_rate.calculate_rate("USD", "AUD"))
    print(e_exchange_rate.calculate_rate("AUD", "USD"))
    print(e_exchange_rate.calculate_rate("BTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("DOGE", "BTC"))
    print(e_exchange_rate.calculate_rate("DOGE", "LTC"))
    print(e_exchange_rate.calculate_rate("LTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("LTC", "SOMECRAP"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "LTC"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "CRAP2"))
    """



    #print(e_exchange_rate.calculate_rate("BTC", "NVC"))

    """
    print(e_exchange_rate.coinbase("BTC", "USD"))
    exit()
    print(e_exchange_rate.btc_value)
    print(e_exchange_rate.load_btc_value())
    exit()

    print(e_exchange_rate.calculate_rate("DOGE", "USD"))
    print(e_exchange_rate.calculate_rate("USD", "DOGE"))
    print(e_exchange_rate.calculate_rate("USD", "AUD"))
    print(e_exchange_rate.calculate_rate("AUD", "USD"))
    print(e_exchange_rate.calculate_rate("BTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("DOGE", "BTC"))
    print(e_exchange_rate.calculate_rate("DOGE", "LTC"))
    print(e_exchange_rate.calculate_rate("LTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("LTC", "SOMECRAP"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "LTC"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "CRAP2"))
    """

    """
    time.sleep(20)
    #

    
    #print(trimmed_mean([Decimal('0.394862'), Decimal('179015'), Decimal('0.6098969444'), Decimal('0.6051244045')]))

    print(e_exchange_rate.calculate_rate("DOGE", "USD"))
    print(e_exchange_rate.calculate_rate("USD", "DOGE"))
    print(e_exchange_rate.calculate_rate("USD", "AUD"))
    print(e_exchange_rate.calculate_rate("AUD", "USD"))
    print(e_exchange_rate.calculate_rate("BTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("DOGE", "BTC"))
    print(e_exchange_rate.calculate_rate("DOGE", "LTC"))
    print(e_exchange_rate.calculate_rate("LTC", "DOGE"))
    print(e_exchange_rate.calculate_rate("LTC", "SOMECRAP"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "LTC"))
    print(e_exchange_rate.calculate_rate("SOMECRAP", "CRAP2"))
    """


    """
589.3411754999087 btc/nvc
0.0002318244250000000 doge/usd
4313.609318776484 usd/doge
1.307018690367272 usd/aud
0.7651            aud/usd
1544401.544401544 btc/doge
6.4750000000E-7      doge/btc
1.379041744231990E-8  doge/ltc
72514121.06867842     ltc/doge
0
0
0

0.003999991175217078
277960219.066036
3.597637112821624E-9
1.2116072
0.8253499979201180
0.000001288062015503526
776360.1348100327
165604197.8939269
6.038494269574748E-9
0
0
0

    """

    """
There's another error with the exchange rate code. It's returning zero again -- it doesn't seem to be getting the slow handlers or something like that

The code seems to only work when its initialized with LTC / BTC. Why would this be the case?

    The problem seems to be when BTC isn't the first currency. You need code to detect it and flip it

    Extra pairs need to be coverted to USD too! The results aren't optimal!

    """


    """

    print("Google")
    print(e_exchange_rate.google("BTC", "USD"))
    print()

    print("Yahoo")
    print(e_exchange_rate.yahoo("BTC", "USD"))

    print("xe")
    print(e_exchange_rate.xe("AUD", "USD"))

    print("yahoo")
    print(e_exchange_rate.yahoo("AUD", "USD"))

    print("dustcoin")
    print(e_exchange_rate.dustcoin("DOGE", "BTC")["rate"])

    print("Bloomberg")
    print(e_exchange_rate.bloomberg("DOGE", "BTC")["rate"])


    """

    """
    print("bter")
    print(e_exchange_rate.bter("DOGE", "BTC")["rate"])

    print("coinmarketcap")
    print(e_exchange_rate.coinmarketcap("DOGE", "BTC")["rate"])

    print("coinpayments")
    print(e_exchange_rate.coinpayments("DOGE", "BTC")["rate"])

    print("coins_e")
    print(e_exchange_rate.coins_e("DOGE", "BTC")["rate"])

    print("cryptocoincharts")
    print(e_exchange_rate.cryptocoincharts("DOGE", "BTC")["rate"])

    print("cryptsy")
    print(e_exchange_rate.cryptsy("DOGE", "BTC")["rate"])

    print("ecb")
    print(e_exchange_rate.ecb("DOGE", "BTC")["rate"])

    print("openexchangerates")
    print(e_exchange_rate.openexchangerates("DOGE", "BTC")["rate"])

    print("vircurex")
    print(e_exchange_rate.vircurex("DOGE", "BTC")["rate"])

    print("Bittrex")
    print(e_exchange_rate.bittrex("DOGE", "BTC")["rate"])
    """

    


