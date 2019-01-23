from dataclasses import dataclass, field
from pprint import pprint
from typing import Optional, List
from collections import deque

from web3 import Web3

from monitoring_service.utils.blockchain_listener import get_events


@dataclass
class MonitorRequest:
    reward: int = 0


@dataclass
class Channel:
    channel_identifier: int
    channel_state: int = 0
    on_chain_confirmation: bool = True
    monitor_request: Optional[MonitorRequest] = None


class DB:
    def __init__(self):
        self.channels: List[Channel] = []

    def store_channel(self, channel: Channel):
        try:
            index = self.channels.index(channel)
            self.channels[index] = channel
        except ValueError:
            self.channels.append(channel)

    def get_channel(self, channel_id: int) -> Optional[Channel]:
        for c in self.channels:
            if c.channel_identifier == channel_id:
                return c

        return None

    def __repr__(self):
        return '<DB [{}]>'.format(', '.join(str(e) for e in self.channels))


@dataclass
class BCListener:
    """ This is pull-based instead of push-based."""

    web3: Web3 = None

    registry_address: str = ''
    network_addresses: List[str] = field(default_factory=list)

    def get_events(self, from_block, to_block) -> List:
        # TODO: properly handle new token networks
        result = []

        events = get_events(
            web3=self.web3,
            contract_address=contract,
            topics=topics,
            from_block=from_block + 1,
            to_block=to_block + 1,
        )

        for raw_event in events:
            decoded_event = decode_event(
                self.contract_manager.get_contract_abi(self.contract_name),
                raw_event,
            )
            log.debug('Received confirmed event: \n%s', decoded_event)
            result.append(decoded_event)

        return result


@dataclass
class MSState:
    db: DB
    bcl: BCListener
    latest_known_block: int = 0
    event_queue: deque = deque()


class Event:
    pass


@dataclass
class BlockchainChannelOpenEvent(Event):
    channel_id: int


@dataclass
class BlockchainChannelClosedEvent(Event):
    channel_id: int


@dataclass
class OffchainMonitorRequest(Event):
    channel_id: int
    reward: int


class EventHandler:
    def handle_event(self, event: Event):
        raise NotImplementedError


@dataclass
class ChannelOpenEventHandler(EventHandler):
    state: MSState

    def handle_event(self, event: Event):
        if isinstance(event, BlockchainChannelOpenEvent):
            self.state.db.store_channel(
                Channel(event.channel_id)
            )


@dataclass
class ChannelClosedEventHandler(EventHandler):
    state: MSState

    def handle_event(self, event: Event):
        if isinstance(event, BlockchainChannelClosedEvent):
            channel = self.state.db.get_channel(event.channel_id)

            if channel and channel.on_chain_confirmation:
                print('Trying to monitor channel: ', channel.channel_identifier)
                channel.channel_state = 1

                self.state.db.store_channel(channel)
            else:
                print('Closing channel not confirmed')


@dataclass
class MonitorRequestEventHandler(EventHandler):
    state: MSState

    def handle_event(self, event: Event):
        if isinstance(event, OffchainMonitorRequest):
            channel = self.state.db.get_channel(event.channel_id)

            request = MonitorRequest(reward=event.reward)
            if channel:
                channel.monitor_request = request

                self.state.db.store_channel(channel)
            else:
                # channel has not been confirmed on BC yet
                # wait for PC confirmation
                c = Channel(
                    event.channel_id,
                    on_chain_confirmation=False,
                    monitor_request=request
                )
                self.state.db.store_channel(c)


db = DB()
bcl = BCListener()
s = MSState(db, bcl)
eh1 = ChannelOpenEventHandler(s)
eh2 = MonitorRequestEventHandler(s)
eh3 = ChannelClosedEventHandler(s)

e1 = BlockchainChannelOpenEvent(channel_id=1)
e2 = OffchainMonitorRequest(channel_id=1, reward=5)
e3 = BlockchainChannelClosedEvent(channel_id=1)
e4 = OffchainMonitorRequest(channel_id=2, reward=1)
e5 = BlockchainChannelClosedEvent(channel_id=2)


handlers = {
    BlockchainChannelOpenEvent: eh1,
    BlockchainChannelClosedEvent: eh3,
    OffchainMonitorRequest: eh2,
}

events = [e1, e2, e3, e4, e5]

s.event_queue.extend(events)

def loop():
    new_block = False
    if new_block:
        # events = s.bcl.get_events(s.latest_known_block, new_block)
        # TODO: transform BC events to event machine events

        s.event_queue.extend(events)
        # TODO: append NewBlock event, that increases s.latest_known_block


    # Process all events
    while len(s.event_queue) > 0:
        event = s.event_queue.pop()

        print('>---------------')
        handler: EventHandler = handlers[type(event)]
        handler.handle_event(event)
        pprint(db.channels)


loop()