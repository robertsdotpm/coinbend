import argparse

if __name__ != "__main__":
    #Setup parser.
    parser = argparse.ArgumentParser(prog='main.py')

    #Option: Config files.
    parser.add_argument('-config', '--config', action="store", dest="config", help="query string", default=None)

    #Option: interface.
    parser.add_argument('-interface', '--interface', action="store", dest="interface", help="query string", default=None)

    #Option: node type.
    parser.add_argument('-nodetype', '--nodetype', action="store", dest="node_type", help="query string", default=None)

    #Option: nat type.
    parser.add_argument('-nattype', '--nattype', action="store", dest="nat_type", help="query string", default=None)

    #Option: UI port.
    parser.add_argument('-uiport', '--uiport', action="store", dest="ui_port", help="query string", default=None)

    #Option: UI bind.
    parser.add_argument('-uibind', '--uibind', action="store", dest="ui_bind", help="query string", default=None)

    #Option: passive port.
    parser.add_argument('-passiveport', '--passiveport', action="store", dest="passive_port", help="query string", default=None)

    #Option: passive bind.
    parser.add_argument('-passivebind', '--passivebind', action="store", dest="passive_bind", help="query string", default=None)

    #Option: direct port.
    parser.add_argument('-directport', '--directport', action="store", dest="direct_port", help="query string", default=None)

    #Option: direct bind.
    parser.add_argument('-directbind', '--directbind', action="store", dest="direct_bind", help="query string", default=None)

    #Option: toggle debug.
    parser.add_argument('-debug', '--debug', action="store", dest="debug", help="query string", default=None)

    #Option: toggle testnet.
    parser.add_argument('-testnet', '--testnet', action="store", dest="testnet", help="query string", default=None)

    #Option: flat file.
    parser.add_argument('-flatfile', '--flatfile', action="store", dest="flatfile", help="query string", default=None)

    #Option: max inbound p2p connections.
    parser.add_argument('-maxinbound', '--maxinbound', action="store", dest="max_inbound", help="query string", default=None)

    #Option: max outbound p2p connections.
    parser.add_argument('-maxoutbound', '--maxoutbound', action="store", dest="max_outbound", help="query string", default=None)

    #Option: max direct p2p connections.
    parser.add_argument('-maxdirect', '--maxdirect', action="store", dest="max_direct", help="query string", default=None)

    #Option: local only -- for testing on LAN and single computers.
    parser.add_argument('-localonly', '--localonly', action="store", dest="local_only", help="query string", default=None)

    #Option: data directory.
    parser.add_argument('-datadir', '--datadir', action="store", dest="data_dir", help="query string", default=None)

    #Option: rendezvous servers.
    parser.add_argument('-rendezvous', '--rendezvous', action="store", dest="rendezvous", help="query string", default=None)

    #Option: persona.
    parser.add_argument('-persona', '--persona', action="store", dest="persona", help="query string", default=None)

    #Option: fast load.
    parser.add_argument('-fastload', '--fastload', action="store", dest="fastload", help="query string", default=None)

    #Option: skip network.
    parser.add_argument('-skipnet', '--skipnet', action="store", dest="skipnet", help="query string", default=None)

    #Option: skip bootstrap.
    parser.add_argument('-skipbootstrap', '--skipbootstrap', action="store", dest="skipbootstrap", help="query string", default=None)

    #Option: skip fowarding.
    parser.add_argument('-skipforwarding', '--skipforwarding', action="store", dest="skipforwarding", help="query string", default=None)

    #Option: skip DHT.
    parser.add_argument('-skipdht', '--skipdht', action="store", dest="skipdht", help="query string", default=None)

    #Option: disable e_exchange_rate init
    parser.add_argument('-externalexchange', '--externalexchange', action="store", dest="externalexchange", help="query string", default=None)

    #Option: disable coins init
    parser.add_argument('-coins', '--coins', action="store", dest="coins", help="query string", default=None)

    #Option: clock skew.
    parser.add_argument('-clockskew', '--clockskew', action="store", dest="clockskew", help="query string", default=None)

    #Option: WAN IP.
    parser.add_argument('-wanip', '--wanip', action="store", dest="wanip", help="query string", default=None)

    #Option: external exchange rate init.
    parser.add_argument('-erateinit', '--erateinit', action="store", dest="erateinit", help="query string", default=None)

    #Option: trade to place.
    parser.add_argument('-trade', '--trade', action="store", dest="trade", help="query string", default=None)

    #Option: add nodes.
    parser.add_argument('-addnode', '--addnode', action="store", dest="addnode", help="query string", default=None)

    #Option: use local time - disables NTP.
    parser.add_argument('-uselocaltime', '--uselocaltime', action="store", dest="uselocaltime", help="query string", default=None)

    #Option: demo mode.
    parser.add_argument('-demo', '--demo', action="store", dest="demo", help="query string", default=None)

    #Option: skip main.
    parser.add_argument('-skipmain', '--skipmain', action="store", dest="skipmain", help="query string", default=None)

    #Parse arguments.
    args = args, unknown = parser.parse_known_args()
