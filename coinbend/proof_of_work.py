"""
Bitmessage-style proof of work system for arbitrary messages.
Coinbend uses POW as a way of reducing network abuse for all
messages which have a large potential resources usage. Examples
include messages which need to be broadcast and messages which
causes a node to temporarily store trades on disk. In the future
POW will be combined with some kind of network fee structure
to compensate nodes for storing trades.

Notes: the hash algorithm used for the trial value is sha512.
Most of the code for this module was taken verbatim from 
c306062282d2041a6121e9891fabf3195e601eac with small changes
for Coinbend. For more information see the proof of work
section on the Bitmessage wiki:
https://bitmessage.org/wiki/Proof_of_work
"""

import hashlib
from struct import unpack, pack
import sys

class ProofOfWork():
    def __init__(self, max_cores=4, difficulty=1):
        self.difficulty = difficulty
        self.max_cores = max_cores
        self.nonce_trials_per_byte = 1000 * self.difficulty
        self.payload_length_extra_bytes = 1000 * self.difficulty

    def set_idle(self):
        if 'linux' in sys.platform:
            import os
            os.nice(20)  # @UndefinedVariable
        else:
            try:
                sys.getwindowsversion()
                import win32api,win32process,win32con  # @UnresolvedImport
                pid = win32api.GetCurrentProcessId()
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
                win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
            except:
                #Windows 64-bit
                pass

    def calculate(self, msg, ttl=5*60):
        if type(msg) == str:
            msg = msg.encode("ascii")
        if ttl < 300:
            ttl = 300
        target = (2 ** 64) / (self.nonce_trials_per_byte * (len(msg) + self.payload_length_extra_bytes + ((ttl * (len(msg) + self.payload_length_extra_bytes)) / (2 ** 16))))
        initial_hash = hashlib.sha512(msg).digest()
        return self.do_fast(target, initial_hash)

    def is_valid(self, msg, nonce, ttl=5*60, nonce_trials_per_byte=0, payload_length_extra_bytes=0):
        if type(msg) == str:
            msg = msg.encode("ascii")

        if nonce_trials_per_byte < self.nonce_trials_per_byte:
            nonce_trials_per_byte = self.nonce_trials_per_byte

        if payload_length_extra_bytes < self.payload_length_extra_bytes:
            payload_length_extra_bytes = self.payload_length_extra_bytes

        initial_hash = hashlib.sha512(msg).digest() 
        proof_of_work, = unpack('>Q', hashlib.sha512(hashlib.sha512(pack('>Q', nonce) + initial_hash).digest()).digest()[0:8])

        return proof_of_work <= 2 ** 64 / (nonce_trials_per_byte * (len(msg) + payload_length_extra_bytes + ((ttl * (len(msg) + payload_length_extra_bytes)) / (2 ** 16))))

    def pool_worker(self, nonce, initial_hash, target, pool_size):
        self.set_idle()
        trial_value = float('inf')
        while trial_value > target:
            nonce += pool_size
            trial_value, = unpack('>Q', hashlib.sha512(hashlib.sha512(pack('>Q', nonce) + initial_hash).digest()).digest()[0:8])
        return nonce

    def do_safe(self, target, initial_hash):
        nonce = 0
        trial_value = float('inf')
        while trial_value > target:
            nonce += 1
            trial_value, = unpack('>Q', hashlib.sha512(hashlib.sha512(pack('>Q', nonce) + initial_hash).digest()).digest()[0:8])
        return nonce

    def do_fast(self, target, initial_hash):
        import time
        from multiprocessing import Pool, cpu_count
        try:
            pool_size = cpu_count()
        except:
            pool_size = 4
        if pool_size > self.max_cores:
            pool_size = self.max_cores
        pool = Pool(processes=pool_size)
        result = []
        for i in range(pool_size):
            result.append(pool.apply_async(self.pool_worker, args = (i, initial_hash, target, pool_size)))
        while True:
            for i in range(pool_size):
                if result[i].ready():
                    result = result[i].get()
                    pool.terminate()
                    pool.join() #Wait for the workers to exit...
                    return result
            time.sleep(0.2)

if __name__ == "main":
    max_cores = 4
    x = ProofOfWork(max_cores)
    msg = "I liek cats."
    trial_value, nonce = x.calculate(msg)
    print(x.is_valid(msg, nonce)) 

