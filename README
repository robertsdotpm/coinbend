# Coinbend

![Coinbend UI](http://www.coinbend.com/screenshot.png)

Coinbend is an experimental, high security, decentralized exchange for trading cryptocurrencies that lets complete strangers trade coins with each other without the risk of fraud. It works by using a special combination of time-based cryptography along with a bunch of game theory to allow trades to take place with conventional smart contracts, thereby avoiding the need for a middleman to be trusted with a customer’s deposits when exchanging money.

The exchange was built in response to the numerous hacks and scams that have plagued the Bitcoin world and was built specifically to avoid the need for a third-party to be trusted with any leverage over a customer's money. The software is currently in an an experimental state and lacks a proper order book so users must find each other through another channel to trade but the software is working so I'm releasing this as version 0.001.

Consider this the first practical and true P2P exchange for alt-coins. All existing attempts make unrealistic assumptions about attackers, require the use of collateral as a fail-safe, or strictly depend on third-party trust to exchange currencies (either directly or indirectly as a side-effect of transaction malleability) but Coinbend avoids these problems through the use of modified micro-payment channels and timechain enforced refunds.

> "In crypto with trust."

... or something like that.

### Version
Pre-alpha v0.01

### Build
Coinbend uses Vagrant for reproducible development environments. Vagrant is like automation for VirtualBox and means you can have project specific developer environments that you can bring up with a single command. Especially useful for Coinbend which has a lot of dependencies that could easily break across environments.

First, fork the project to your Github and clone it.

```sh
mkdir coinbend-vagrant
cd coinbend-vagrant
git clone [your-forked-copy-of-coinbend]
```

Install the dependencies you need for Vagrant and Virtual box.

```sh
sudo apt-get install virtualbox vagrant
```

To have the virtual machine downloaded and setup for Coinbend develop:
```sh
cd coinbend/vagrant
sudo vagrant up
```

This command will take a while to complete as it has to download Python3.3 from scratch, compile it, install all the Python packages, download Litecoin + Dogecoin, plus do a lot of other stuff.

You can now make changes to the code with your favourite editor on your main OS and when you need to test the changes you can type sudo vagrant ssh to open a shell prompt to the VM. The VM already has everything needed to run the software from source so it's easy to hack the code.

## Hacking

When you first login to the custom VM it will start up Litecoin and Dogecoin on the testnet + setup a number of virtual interfaces. Coinbend is currently designed to work dynamically with full node cryptocurrencies so unfortunately you will have to wait for the blockchains to download. On fast Internet that's around a few hours of waiting but on a slow PC + Internet its incredibly painful: around 1 - 2 days of waiting for the chains to download and validate.

```sh
# 1 sep 2015 - blocks you need to DL.
# There will be a better way to develop Coinbend without full chains in the future.
vagrant@precise32:~$ /home/vagrant/coins/litecoin/bin/litecoin-cli getinfo
{
    "blocks" : 682511
}

vagrant@precise32:~$ /home/vagrant/coins/dogecoin/bin/dogecoin-cli getinfo
{
    "blocks" : 706056
}

```

After you login a number of virtual interfaces wil ble created. This allows you to simulate the interactions of nodes on a P2P network via the command line and by default IPs bound to eth1 and eth1:x will be accessible from your main / host OS so accessing the web UI of the software is as easy as visiting the IP in your browser.

To start the software for the first time:
```sh
vagrant@precise32:~$ cd /vagrant/coinbend
vagrant@precise32:~$ ifconfig | pcregrep -M "eth1:1[\s\S]*?inet addr"
eth1:1    Link encap:Ethernet  HWaddr ...  
          inet addr:192.168.1.147  Bcast:192.168.255.0  Mask:255.255.255.255

vagrant@precise32:~$ python3.3 -m "coinbend.main" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -1 -interface eth1:1 -uibind 192.168.1.147 -passivebind 192.168.1.147 -directbind 192.168.1.147 -skipbootstrap 1 -localonly 1 -uselocaltime 1
...
Web server started.
Bottle v0.13-dev server starting up (using WSGIRefServer())...
Listening on http://192.168.1.147:7777/
```

And here's how it looks in the browser:
* Alice demo - http://alice.coinbend.com/
* Bob demo - http://bob.coinbend.com/

At this point you want to go to some faucets and send testcoins to your account addresses. Shoot me an email at matthew@roberts.pm if you need some testcoins or generate them yourself:
```sh
# Don't run them both at the same time - it will be too slow!
vagrant@precise32:~$ /home/vagrant/coins/litecoin/bin/litecoin-cli setgenerate true
vagrant@precise32:~$ /home/vagrant/coins/dogecoin/bin/dogecoin-cli setgenerate true
```

##### How to trade with yourself

Once you have a positive balance open two shells to your vagrant VM and do the following:
```sh
# Shell 1 - Alice
vagrant@precise32:~$ python3.3 -m "coinbend.main" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -1 -interface eth1:1 -uibind 192.168.1.147 -passivebind 192.168.1.147 -directbind 192.168.1.147 -skipbootstrap 1 -localonly 1 -uselocaltime 1 -nodetype passive -trade "buy 200 dogecoin/litecoin @ 0.005"

# Shell 2 - Bob
vagrant@precise32:~$ python3.3 -m "coinbend.main" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -1 -interface eth1:2 -uibind 192.168.1.148 -passivebind 192.168.1.148 -directbind 192.168.1.148 -skipbootstrap 1 -localonly 1 -uselocaltime 1 -nodetype passive -trade "sell 200 dogecoin/litecoin @ 0.005" -addnode passive://192.168.1.147:50500/p2p
```

These command line arguments tell the software not to calculate the exchange rate; not to detect the clock skew for the system clock; to bind to a specific virtual interface; to skip trying to find other nodes on the P2P network; to use LAN IP addresses for trade messages instead of WAN IPs (because WAN IPs don't work behind the same router); to switch the node type to passive (meaning you can accept inbound connections); to open a new order; and for Bob to connect to Alice.

##### Trading via the UI

1. Alice UI: http://192.168.1.147:7777 
2. Bob UI: http://192.168.1.148:7777
3. Alice: open a new order to buy 200 Dogecoins at 0.001 Litecoins per Dogecoin. Click submit. A confirmation dialogue will pop up.
4. Alice: at the bottom of the confirm dialogue click "generate copy of Node ID"
5. Alice: cnt + c
6. Bob: open a sell order to sell 200 Dogecoins at 0.001 Litecoins per Dogecoin. Click submit. A new confirmation dialogue will pop up.
7. Bob: cnt + v into the input box to paste Alice's node ID.
8. Bob: click "generae copy of Node ID"
9. Bob: cnt + c
10. Alice: cnt + v into the input box to paste Bob's node ID.
11. Submit the trade on both windows.

Video guide is here: https://www.youtube.com/watch?v=h7maCX8XKbg

This is how I test the software most of the time (I told you this was experimental.)

### A brief primer on what everything is

Infrastructure for the project consists of 3 main components:
* Rendezvous server - used by nodes to connect to the p2p network
* Contract server - makes contracts more atomic + fixes a few security edge cases
* UI server - light weight bottle.py web server that hosts the UI

Folder structure:
* coinbend - all the main code
* install/www - has all the UI stuff / web modules or what you see on *:7777/satoshi
* server - code that runs on www.coinbend.com
* ~/.Coinbend - data directory on Linux. %appdata%\Coinbend on Windows.

What file are:
* main.py - the entry point to the whole program.
* build_binary.py - used to build platform specifc binaries for the software. Run sudo python3.3 build_binary.py build on the VM.
* net.py - class uses to provide p2p networking
* sock.py - provides a custom socket wrapped. Coinbend uses non-blocking sockets
* exchange_rate.py - gets the exchange rate for currencies from multiple sources. Uses a trimmed average for rates
* address.py - serialises and detribalises addresses between cryptocurrencies
* args.py - command line arguments for the software
* coin_config.py - parses + patches coins config files for RPC connectivity
* coinlib.py - functions for working with raw transactions
* contract_client.py - talking to the contract server so people can't waste each other's time
* contract_server.py - checks contracts and releases info needed to carry out contract
* cryptocurrencies.py - list of cryptocurrencies and associated currency codes
* currency_type.py - custom library for doing floating point operations as integer
* database.py - custom DB wrapper for forcing serializable, ACID transactions
* ecdsa_crypt.py - serializes and deserializes ECDSA pairs making signing simple
* fiatcurrencies.py - list of fiatcurrencies and their codes
* globals.py - list of module wide global variables
* green_address.py - provides a secure clearing house prior to setting up contracts
* hybrid_protocol.py - the networking protocol for the entire project
* hybrid_reply - dynamic replies from the protocol with complex routing behaviour
* ipgetter.py - gets the WAN IP
* json_rpc.py - wrapped for JSON RPC python library that fixes timeout bugs
* lib.py - small functions that dont fit in any specific module
* match_stype.py - handles state transitions for matches
* match_type.py - what a match looks like on the exchange
* microtransfer_contract.py - the magic file implementing Coinbend smart contracts
* nat_pmp.py - NAT hole punching with NAT-PMP
* order_book.py - saves orders (trades submitted to the main network) to a simple replicating DB
* order_type.py - what an order looks like
* parse_config.py - parses the main config file for the software into an immutable state
* password_complexity.py - designed for building secure passwords
* private_key.py - working with wallet-style private keys
* proof_of_work.py - calculating and verifying sha256-style proof-of-work
* rendezvous_client.py - talking to the rendezvous server to find p2p nodes
* rendezvous_server.py - custom server that supports TCP hole punching for NAT traversal + gives clietns fresh nodes to connect to the p2p network
* sys_clock.py - determines how much clock skew you have compared to a global NTP time
* trade_engine.py - handles opening trades and recording them
* trades.py - a collection of the users open trades
* trade_type.py - special type for serializing and deserializing trades. Also supports matching
* tx_monitor.py - event based, multi-currency, transaction monitor
* tx_push.py - push a tx to a p2p network using the raw protocol
* unl.py - universal node locator - used to connect to nodes
* upnp.py - uses UPnP to do NAT traversal
* user.py - creates a new user on Coinbend
* username_complexity.py - ensures usernames are unique and can't be brute forced
* user_web_server.py - the main web app for the UI. Also supports routes and API calls

> So then ... there's no real documentation? Unfortunately no. As you can see: there's a lot of modules and a lot of code and I'm the only developer but its definitely on my todo list.

Papers:
Coinbend white paper - www.coinbend.com/whitepaper.pdf
Timechain white paper - www.roberts.pm/timechain

### Development
Want to contribute? Great!

Contract me at matthew@roberts.pm if you need any help.

### License
There's no license yet but all the code will be release under LGPL soon (when I have time.) The UI won't be released under an open source license but it will be free to use and download.

