import heapq
import threading
import time

from .peer import Peer
from .hashing import id_from_addr

def largest_differing_bit(value1, value2):
    distance = value1 ^ value2
    length = -1
    while (distance):
        distance >>= 1
        length += 1
    return max(0, length)

class BucketSet(object):
    def __init__(self, bucket_size, buckets, id, valid_bind_ports):
        self.id = id
        self.bucket_size = bucket_size
        self.buckets = [list() for _ in range(buckets)]
        self.lock = threading.Lock()
        self.seen_ids = {}
        self.seen_ips = {}
        self.max_entries_per_ip = 2
        self.valid_bind_ports = valid_bind_ports

        #Maps nodes to timestamp.
        self.node_freshness = [] 
        
    def insert(self, peer):
        if peer.id != self.id:
            with self.lock:
            #Find peer details.
                peer_triple = peer.astriple()
                peer_addr = peer_triple[0:2]
                peer_id = peer_triple[2]

                #Unique peer ID is required.
                if peer_id in self.seen_ids:
                    return

                #Too many routing entries for same IP.
                peer_host = peer_addr[0]
                peer_port = int(peer_addr[1])
                if peer_host in self.seen_ips:
                    if len(self.seen_ips[peer_host]) >= self.max_entries_per_ip:
                        if peer_port not in self.seen_ips[peer_host]:
                            return
                else:
                    self.seen_ips[peer_host] = []

                #Invalid port -- helps prevent route table spamming.
                if peer_port not in self.valid_bind_ports:
                    return

                #Invalid ID -- helps prevent Sybil attacks.
                expected_id = id_from_addr(peer_host, peer_port)
                if int(peer_id) != expected_id:
                    return

                #Insert triplet into bucket.
                bucket_number = largest_differing_bit(self.id, peer.id)

                #Record node in routing table.
                bucket = self.buckets[bucket_number]
                if peer_triple in bucket: 
                    bucket.pop(bucket.index(peer_triple))
                elif len(bucket) >= self.bucket_size:
                    bucket.pop(0)
                bucket.append(peer_triple)

                #Bookkeeping for spam prevention.
                self.seen_ids[peer_id] = bucket_number
                if peer_port not in self.seen_ips[peer_host]:
                    self.seen_ips[peer_host].append(peer_port)

                #Record node freshness for efficient pings.
                freshness = {
                    "timestamp": time.time(),
                    "bucket_no": bucket_number,
                    "node": peer_triple
                }
                self.node_freshness.append(freshness)
                
    def nearest_nodes(self, key, limit=None):
        num_results = limit if limit else self.bucket_size
        with self.lock:
            def keyfunction(peer):
                return key ^ peer[2] # ideally there would be a better way with names? Instead of storing triples it would be nice to have a dict
            peers = (peer for bucket in self.buckets for peer in bucket)
            best_peers = heapq.nsmallest(self.bucket_size, peers, keyfunction)
            return [Peer(*peer) for peer in best_peers]


