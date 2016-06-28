import asyncio
import logging

import hbmqtt.client
from . import AbstractActor

LOG = logging.getLogger(__name__)


class MqttActor(AbstractActor):
    def __init__(self):
        self.mqtt_client = None

    def init(self, config, context):
        self.config = config
        self.context = context

        self.mqtt_client = hbmqtt.client.MQTTClient(config={'auto_reconnect': True,
                                                            'reconnect_max_interval': 10,
                                                            'reconnect_retries': 500})

    @asyncio.coroutine
    def loop(self):
        connected = False
        while self.running:
            if not connected:
                connected = yield from self.connect()
            try:
                message = yield from self.mqtt_client.deliver_message()
                packet = message.publish_packet
                topic = packet.variable_header.topic_name
                value = packet.payload.data.decode('utf-8')
                self.check_topic(topic, value)
            except hbmqtt.client.ClientException as ce:
                LOG.error('Client exception: %s' % ce)
                connected = False
            except Exception as e:
                LOG.error('%s' % e)
                connected = False
            if not connected:
                yield from self.disconnect()
        yield from self.disconnect()

    @asyncio.coroutine
    def connect(self):
        try:
            yield from self.mqtt_client.connect(self.config['mqtt']['url'])
            yield from self.mqtt_client.subscribe([
                ('#', 0),
                ('#', 1),
            ])
            LOG.info('connected')
            return True
        except:
            LOG.exception('error on connect')
            return False

    @asyncio.coroutine
    def disconnect(self):
        try:
            yield from self.mqtt_client.disconnect()
        except:
            LOG.exception('error on disconnect')

    def check_topic(self, topic, value):
        LOG.debug('got topic %s, message %s', topic, value)
        for t in self.context.items:
            if t.input == 'mqtt:%s' % topic:
                self.context.set_item_value(t['name'], value)

    def is_my_command(self, cmd, arg):
        return cmd.startswith('mqtt:')

    @asyncio.coroutine
    def command(self, cmd, arg):
        yield from self.mqtt_client.publish(cmd[5:], arg.encode('UTF-8'), 0)
