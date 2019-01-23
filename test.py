import dataclasses
from pprint import pprint
from typing import Optional, List


@dataclasses.dataclass
class MonitorRequest:
    reward: int = 0


@dataclasses.dataclass
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

class Event:
    pass


@dataclasses.dataclass
class BlockchainChannelOpenEvent(Event):
    channel_id: int


@dataclasses.dataclass
class BlockchainChannelClosedEvent(Event):
    channel_id: int


@dataclasses.dataclass
class OffchainMonitorRequest(Event):
    channel_id: int
    reward: int


class EventHandler:
    def handle_event(self, event: Event):
        raise NotImplementedError


@dataclasses.dataclass
class ChannelOpenEventHandler(EventHandler):
    db: DB

    def handle_event(self, event: Event):
        if isinstance(event, BlockchainChannelOpenEvent):
            self.db.store_channel(
                Channel(event.channel_id)
            )


@dataclasses.dataclass
class ChannelClosedEventHandler(EventHandler):
    db: DB

    def handle_event(self, event: Event):
        if isinstance(event, BlockchainChannelClosedEvent):
            channel = self.db.get_channel(event.channel_id)

            if channel and channel.on_chain_confirmation:
                print('Trying to monitor channel: ', channel.channel_identifier)
                channel.channel_state = 1

                self.db.store_channel(channel)
            else:
                print('Closing channel not confirmed')


@dataclasses.dataclass
class MonitorRequestEventHandler(EventHandler):
    db: DB

    def handle_event(self, event: Event):
        if isinstance(event, OffchainMonitorRequest):
            channel = self.db.get_channel(event.channel_id)

            request = MonitorRequest(reward=event.reward)
            if channel:
                channel.monitor_request = request

                self.db.store_channel(channel)
            else:
                # channel has not been confirmed on BC yet
                c = Channel(
                    event.channel_id,
                    on_chain_confirmation=False,
                    monitor_request=request
                )
                self.db.store_channel(c)


db = DB()
eh1 = ChannelOpenEventHandler(db)
eh2 = MonitorRequestEventHandler(db)
eh3 = ChannelClosedEventHandler(db)

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

pprint(db.channels)
for event in events:
    print('>---------------')
    handler: EventHandler = handlers[type(event)]

    handler.handle_event(event)
    pprint(db.channels)