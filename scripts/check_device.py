"""Check a Lichen Play on your network with the integration's protocol client.

Needs only Python 3.11 or later, no Home Assistant. Run from the repository root:

    python3 scripts/check_device.py 192.168.1.137

By default it only reads from the device. Options:

    --key N        the private key, if you have it (Home Assistant stores it in
                   config/.storage/core.config_entries, "private_key")
    --port N       device port (default 1233)
    --test-switch  also turn device eco mode to the opposite setting and back,
                   to check commands work. It never starts watering.

Put the device in setup mode (hold Mode for 2 seconds until the LED flashes)
to also check that the full private key is read.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
from pathlib import Path
import sys

CLIENT = Path(__file__).resolve().parents[1] / "custom_components" / "playtopro" / "P2PDevice.py"
_spec = importlib.util.spec_from_file_location("p2pdevice", CLIENT)
p2p = importlib.util.module_from_spec(_spec)
sys.modules["p2pdevice"] = p2p
_spec.loader.exec_module(p2p)

THREE_BYTES = 0xFFFFFF
failures = 0


def ok(message: str) -> None:
    print(f"  PASS  {message}")


def fail(message: str) -> None:
    global failures
    failures += 1
    print(f"  FAIL  {message}")


def info(message: str) -> None:
    print(f"        {message}")


def show_status(status) -> None:
    info(
        f"auto mode {'on' if status.system_auto else 'off'}, "
        f"eco mode {'on' if status.eco_mode else 'off'} ({status.eco_mode_factor}%)"
    )
    for zone in status.zones:
        flags = [
            name
            for name, on in (
                ("WATERING", zone.on),
                ("manual", zone.manual_mode_active),
                ("auto", zone.auto_mode),
                ("eco", zone.eco_mode),
                ("sleep", zone.sleep_mode),
            )
            if on
        ]
        info(f"zone {zone.index + 1}: {', '.join(flags) or '-'}")


async def main(host: str, port: int, key: int | None, test_switch: bool) -> None:
    print(f"\n1. Identify the device at {host}:{port}")
    try:
        firmware = await p2p.P2PDevice(host, port, 0).async_get_firmware()
    except p2p.P2PError as err:
        fail(f"no valid reply ({err.error}): {err}")
        return
    ok(f"serial {firmware.serial_number}, firmware {firmware.firmware}")
    if firmware.firmware < 28:
        fail("firmware is older than 28, which the integration doesn't support")
    info("setup mode" if firmware.mode else "normal mode (not setup mode)")

    if firmware.mode:
        if firmware.private_key == 0:
            fail("in setup mode but the device returned no private key")
        else:
            ok(f"private key read in full: {firmware.private_key}")
            if firmware.private_key > THREE_BYTES:
                info(
                    "this key is above 16,777,215: the old version would have saved "
                    f"{firmware.private_key & THREE_BYTES} and lost the connection "
                    "after setup mode"
                )
            else:
                info("this key fits in 3 bytes, so the old version wasn't affected")
            if key is not None and key != firmware.private_key:
                fail(f"--key {key} doesn't match the device's key")
            key = firmware.private_key

    print("\n2. Read the status (using the serial number, which the device allows)")
    try:
        status = await p2p.P2PDevice(host, port, firmware.serial_number).async_get_status()
    except p2p.P2PError as err:
        fail(f"{err.error}: {err}")
    else:
        ok("status decoded")
        show_status(status)

    if key is None:
        print("\n3. Private key: skipped (pass --key, or put the device in setup mode)")
        return

    print("\n3. Check the private key")
    device = p2p.P2PDevice(host, port, key)
    try:
        await device.async_get_status()
    except p2p.P2PRejectedError:
        if firmware.mode:
            fail("rejected, even in setup mode")
        else:
            fail("the device rejected this key; Home Assistant would ask you to reconnect")
        return
    except p2p.P2PError as err:
        fail(f"{err.error}: {err}")
        return
    ok("accepted" + (" (setup mode accepts any key; recheck in normal mode)" if firmware.mode else ""))

    if firmware.mode == 0:
        wrong_key = key ^ 0x5A5A5A5A
        if wrong_key in (0, firmware.serial_number):
            wrong_key = key ^ 0xA5A5A5A5
        try:
            await p2p.P2PDevice(host, port, wrong_key).async_get_status()
        except p2p.P2PRejectedError:
            ok("a wrong key is rejected, which is what triggers reconnect in Home Assistant")
        except p2p.P2PError as err:
            fail(f"unexpected reply to a wrong key: {err.error}")
        else:
            fail("the device accepted a wrong key")

    if not test_switch:
        print("\n4. Commands: skipped (pass --test-switch to toggle eco mode and back)")
        return

    print("\n4. Toggle device eco mode and restore it")
    before = (await device.async_get_status()).eco_mode
    try:
        for target in (not before, before):
            if not await device.async_set_eco_mode(target):
                fail(f"device refused to set eco mode {'on' if target else 'off'}")
                return
            now = (await device.async_get_status()).eco_mode
            if now != target:
                fail(f"eco mode is {'on' if now else 'off'}, expected {'on' if target else 'off'}")
                return
            ok(f"eco mode {'on' if target else 'off'}")
    finally:
        if (await device.async_get_status()).eco_mode != before:
            await device.async_set_eco_mode(before)
    info(f"restored to {'on' if before else 'off'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=1233)
    parser.add_argument("--key", type=int)
    parser.add_argument("--test-switch", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        sys.exit("Python 3.11 or later is needed")
    asyncio.run(main(args.host, args.port, args.key, args.test_switch))
    print(f"\n{'All checks passed.' if not failures else f'{failures} check(s) failed.'}")
    sys.exit(1 if failures else 0)
