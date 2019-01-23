from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa

from typing import Dict, Callable, Optional
from enum import Enum
from queue import PriorityQueue
from eth_utils import to_checksum_address, encode_hex

from web3.middleware import construct_sign_and_send_raw_middleware
from eth_account import Account

from dataclasses import dataclass
from web3 import HTTPProvider, Web3

import getpass
import gevent

# MVP
# - tx need a priority
# - reorder when newer, higher prioritized txs come in

# Later
# - multiple tx may be waiting for mining
# - tx may have conditions to be accepted before submittal


class Priority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(order=True)
class ActiveTx:
    transaction_data: Dict
    submittal_block: Optional[int] = None
    deadline: Optional[int] = None
    priority: Priority = Priority.NORMAL
    transaction_hash: Optional[str] = None


def exponential(increase: float) -> Callable:
    def f(tx):
        return 1

    return f

# PRICE_STRATEGY = price_strategies.exponential(per_hour=1.2)
# ...
# txn_hash = w3.eth.sendTransaction(...)
# gas_daemon.add(txn_hash, PRICE_STRATEGY)


class Daemon(gevent.Greenlet):
    def __init__(self, web3):
        super().__init__()
        self.web3 = web3
        self.queue = PriorityQueue()
        self.stop_event = gevent.event.Event()
        self.active_tx = None

    def add_transaction(self, transaction: ActiveTx):
        self.queue.put(transaction)

    def _run(self):
        print('ABC')
        # this loop will wait until spawned greenlets complete
        while not self.stop_event.is_set():
            print('Unfinished tasks:', self.queue.unfinished_tasks)

            if self.active_tx:
                receipt = self.web3.eth.getTransactionReceipt(self.active_tx.transaction_hash)
                print(receipt)

                if receipt and receipt['blockHash'] and receipt['blockNumber']:
                    self.active_tx = None
                    self.queue.task_done()

            if not self.queue.empty() and self.active_tx is None:
                next_tx: ActiveTx = self.queue.get(block=False)

                tx_hash = self.web3.eth.sendTransaction(next_tx.transaction_data)
                print('Submitted tx: hash:', encode_hex(tx_hash))
                next_tx.transaction_hash = tx_hash

                self.active_tx = next_tx

            gevent.sleep(1)

    def stop(self):
        self.stop_event.set()


import json
path = '/Users/paul/Library/Ethereum/testnet/keystore/UTC--2017-10-04T13-33-48.505688847Z--fb398e621c15e2bc5ae6a508d8d89af1f88c93e8'
with open(path, 'r') as f:
    acct = Account.decrypt(json.load(f), getpass.getpass())

eth_node = 'http://parity.ropsten.ethnodes.brainbot.com:8545'
provider = HTTPProvider(eth_node)
web3 = Web3(provider)
web3.middleware_stack.add(construct_sign_and_send_raw_middleware(acct))

sender = '0xfb398e621c15e2bc5ae6a508d8d89af1f88c93e8'
receiver = '0xdf173a5173c3d0ae5ba11dae84470c5d3f1a8413'

def tx_gen():
    for i in range(20):
        yield {
            'from': to_checksum_address(sender),
            'to': to_checksum_address(receiver),
            'value': i,
        }


d = Daemon(web3)
for _ in range(10):
    d.add_transaction(
        ActiveTx(transaction_data=next(tx_gen()))
    )
d.run()
