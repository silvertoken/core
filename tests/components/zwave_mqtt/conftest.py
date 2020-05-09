"""Helpers for tests."""
import json

import pytest

from .common import MQTTMessage

from tests.async_mock import patch
from tests.common import load_fixture


@pytest.fixture(name="generic_data", scope="session")
def generic_data_fixture():
    """Load generic MQTT data and return it."""
    return load_fixture(f"zwave_mqtt/generic_network_dump.csv")


@pytest.fixture(name="light_data", scope="session")
def light_data_fixture():
    """Load light dimmer MQTT data and return it."""
    return load_fixture(f"zwave_mqtt/light_network_dump.csv")


@pytest.fixture(name="sent_messages")
def sent_messages_fixture():
    """Fixture to capture sent messages."""
    sent_messages = []

    with patch(
        "homeassistant.components.mqtt.async_publish",
        side_effect=lambda hass, topic, payload: sent_messages.append(
            {"topic": topic, "payload": json.loads(payload)}
        ),
    ):
        yield sent_messages


@pytest.fixture(name="light_msg")
async def light_msg_fixture(hass):
    """Return a mock MQTT msg with a light actuator message."""
    light_json = json.loads(
        await hass.async_add_executor_job(load_fixture, "zwave_mqtt/light.json")
    )
    message = MQTTMessage(topic=light_json["topic"], payload=light_json["payload"])
    message.encode()
    return message


@pytest.fixture(name="switch_msg")
async def switch_msg_fixture(hass):
    """Return a mock MQTT msg with a switch actuator message."""
    switch_json = json.loads(
        await hass.async_add_executor_job(load_fixture, "zwave_mqtt/switch.json")
    )
    message = MQTTMessage(topic=switch_json["topic"], payload=switch_json["payload"])
    message.encode()
    return message


@pytest.fixture(name="sensor_msg")
async def sensor_msg_fixture(hass):
    """Return a mock MQTT msg with a sensor change message."""
    sensor_json = json.loads(
        await hass.async_add_executor_job(load_fixture, "zwave_mqtt/sensor.json")
    )
    message = MQTTMessage(topic=sensor_json["topic"], payload=sensor_json["payload"])
    message.encode()
    return message
