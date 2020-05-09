"""Test different accessory types: Camera."""

from uuid import UUID

from pyhap.accessory_driver import AccessoryDriver
import pytest

from homeassistant.components import camera, ffmpeg
from homeassistant.components.homekit.accessories import HomeBridge
from homeassistant.components.homekit.const import (
    AUDIO_CODEC_COPY,
    CONF_AUDIO_CODEC,
    CONF_STREAM_SOURCE,
    CONF_SUPPORT_AUDIO,
    CONF_VIDEO_CODEC,
    VIDEO_CODEC_COPY,
)
from homeassistant.components.homekit.type_cameras import Camera
from homeassistant.components.homekit.type_switches import Switch
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component

from tests.async_mock import AsyncMock, MagicMock, patch

MOCK_START_STREAM_TLV = "ARUCAQEBEDMD1QMXzEaatnKSQ2pxovYCNAEBAAIJAQECAgECAwEAAwsBAgAFAgLQAgMBHgQXAQFjAgQ768/RAwIrAQQEAAAAPwUCYgUDLAEBAwIMAQEBAgEAAwECBAEUAxYBAW4CBCzq28sDAhgABAQAAKBABgENBAEA"
MOCK_END_POINTS_TLV = "ARAzA9UDF8xGmrZykkNqcaL2AgEAAxoBAQACDTE5Mi4xNjguMjA4LjUDAi7IBAKkxwQlAQEAAhDN0+Y0tZ4jzoO0ske9UsjpAw6D76oVXnoi7DbawIG4CwUlAQEAAhCyGcROB8P7vFRDzNF2xrK1Aw6NdcLugju9yCfkWVSaVAYEDoAsAAcEpxV8AA=="
MOCK_START_STREAM_SESSION_UUID = UUID("3303d503-17cc-469a-b672-92436a71a2f6")


@pytest.fixture()
def run_driver(hass):
    """Return a custom AccessoryDriver instance for HomeKit accessory init."""
    with patch("pyhap.accessory_driver.Zeroconf"), patch(
        "pyhap.accessory_driver.AccessoryEncoder"
    ), patch("pyhap.accessory_driver.HAPServer"), patch(
        "pyhap.accessory_driver.AccessoryDriver.publish"
    ), patch(
        "pyhap.accessory_driver.AccessoryDriver.persist"
    ):
        yield AccessoryDriver(
            pincode=b"123-45-678", address="127.0.0.1", loop=hass.loop
        )


def _get_working_mock_ffmpeg():
    """Return a working ffmpeg."""
    ffmpeg = MagicMock()
    ffmpeg.open = AsyncMock(return_value=True)
    ffmpeg.close = AsyncMock(return_value=True)
    ffmpeg.kill = AsyncMock(return_value=True)
    return ffmpeg


def _get_failing_mock_ffmpeg():
    """Return an ffmpeg that fails to shutdown."""
    ffmpeg = MagicMock()
    ffmpeg.open = AsyncMock(return_value=False)
    ffmpeg.close = AsyncMock(side_effect=OSError)
    ffmpeg.kill = AsyncMock(side_effect=OSError)
    return ffmpeg


async def test_camera_stream_source_configured(hass, run_driver, events):
    """Test a camera that can stream with a configured source."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        hass, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(
        hass,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_STREAM_SOURCE: "/dev/null", CONF_SUPPORT_AUDIO: True},
    )
    not_camera_acc = Switch(hass, run_driver, "Switch", entity_id, 4, {},)
    bridge = HomeBridge("hass", run_driver, "Test Bridge")
    bridge.add_accessory(acc)
    bridge.add_accessory(not_camera_acc)

    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]
    working_ffmpeg = _get_working_mock_ffmpeg()

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value=None,
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=working_ffmpeg,
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await hass.async_block_till_done()

    expected_output = (
        "-map 0:v:0 -an -c:v libx264 -profile:v high -tune zerolatency -pix_fmt "
        "yuv420p -r 30 -b:v 299k -bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f "
        "rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtcpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a libopus -application lowdelay -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type "
        "110 -ssrc {a_ssrc} -f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtcpport=51108&pkt_size=188"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
    )

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value="rtsp://example.local",
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=working_ffmpeg,
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        # Calling a second time should not throw
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()

    assert await hass.async_add_executor_job(acc.get_snapshot, 1024)

    # Verify the bridge only forwards get_snapshot for
    # cameras and valid accessory ids
    assert await hass.async_add_executor_job(bridge.get_snapshot, {"aid": 2})
    with pytest.raises(ValueError):
        assert await hass.async_add_executor_job(bridge.get_snapshot, {"aid": 3})
    with pytest.raises(ValueError):
        assert await hass.async_add_executor_job(bridge.get_snapshot, {"aid": 4})


async def test_camera_stream_source_configured_with_failing_ffmpeg(
    hass, run_driver, events
):
    """Test a camera that can stream with a configured source with ffmpeg failing."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        hass, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(
        hass,
        run_driver,
        "Camera",
        entity_id,
        2,
        {CONF_STREAM_SOURCE: "/dev/null", CONF_SUPPORT_AUDIO: True},
    )
    not_camera_acc = Switch(hass, run_driver, "Switch", entity_id, 4, {},)
    bridge = HomeBridge("hass", run_driver, "Test Bridge")
    bridge.add_accessory(acc)
    bridge.add_accessory(not_camera_acc)

    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value="rtsp://example.local",
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=_get_failing_mock_ffmpeg(),
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        # Calling a second time should not throw
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()


async def test_camera_stream_source_found(hass, run_driver, events):
    """Test a camera that can stream and we get the source from the entity."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        hass, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(hass, run_driver, "Camera", entity_id, 2, {},)
    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value="rtsp://example.local",
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=_get_working_mock_ffmpeg(),
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value="rtsp://example.local",
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=_get_working_mock_ffmpeg(),
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()


async def test_camera_stream_source_fails(hass, run_driver, events):
    """Test a camera that can stream and we cannot get the source from the entity."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        hass, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(hass, run_driver, "Camera", entity_id, 2, {},)
    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        side_effect=OSError,
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=_get_working_mock_ffmpeg(),
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()


async def test_camera_with_no_stream(hass, run_driver, events):
    """Test a camera that cannot stream."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(hass, camera.DOMAIN, {camera.DOMAIN: {}})

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(hass, run_driver, "Camera", entity_id, 2, {},)
    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError):
        await hass.async_add_executor_job(acc.get_snapshot, 1024)


async def test_camera_stream_source_configured_and_copy_codec(hass, run_driver, events):
    """Test a camera that can stream with a configured source."""
    await async_setup_component(hass, ffmpeg.DOMAIN, {ffmpeg.DOMAIN: {}})
    await async_setup_component(
        hass, camera.DOMAIN, {camera.DOMAIN: {"platform": "demo"}}
    )

    entity_id = "camera.demo_camera"

    hass.states.async_set(entity_id, None)
    await hass.async_block_till_done()
    acc = Camera(
        hass,
        run_driver,
        "Camera",
        entity_id,
        2,
        {
            CONF_STREAM_SOURCE: "/dev/null",
            CONF_SUPPORT_AUDIO: True,
            CONF_VIDEO_CODEC: VIDEO_CODEC_COPY,
            CONF_AUDIO_CODEC: AUDIO_CODEC_COPY,
        },
    )
    bridge = HomeBridge("hass", run_driver, "Test Bridge")
    bridge.add_accessory(acc)

    await acc.run_handler()

    assert acc.aid == 2
    assert acc.category == 17  # Camera

    acc.set_endpoints(MOCK_END_POINTS_TLV)
    session_info = acc.sessions[MOCK_START_STREAM_SESSION_UUID]

    working_ffmpeg = _get_working_mock_ffmpeg()

    with patch(
        "homeassistant.components.demo.camera.DemoCamera.stream_source",
        return_value=None,
    ), patch(
        "homeassistant.components.homekit.type_cameras.HAFFmpeg",
        return_value=working_ffmpeg,
    ):
        acc.set_selected_stream_configuration(MOCK_START_STREAM_TLV)
        await acc.stop_stream(session_info)
        await hass.async_block_till_done()

    expected_output = (
        "-map 0:v:0 -an -c:v copy -tune zerolatency -pix_fmt yuv420p -r 30 -b:v 299k "
        "-bufsize 1196k -maxrate 299k -payload_type 99 -ssrc {v_ssrc} -f rtp -srtp_out_suite "
        "AES_CM_128_HMAC_SHA1_80 -srtp_out_params zdPmNLWeI86DtLJHvVLI6YPvqhVeeiLsNtrAgbgL "
        "srtp://192.168.208.5:51246?rtcpport=51246&localrtcpport=51246&pkt_size=1316 -map 0:a:0 "
        "-vn -c:a copy -ac 1 -ar 24k -b:a 24k -bufsize 96k -payload_type 110 -ssrc {a_ssrc} "
        "-f rtp -srtp_out_suite AES_CM_128_HMAC_SHA1_80 -srtp_out_params "
        "shnETgfD+7xUQ8zRdsaytY11wu6CO73IJ+RZVJpU "
        "srtp://192.168.208.5:51108?rtcpport=51108&localrtcpport=51108&pkt_size=188"
    )

    working_ffmpeg.open.assert_called_with(
        cmd=[],
        input_source="-i /dev/null",
        output=expected_output.format(**session_info),
        stdout_pipe=False,
    )
