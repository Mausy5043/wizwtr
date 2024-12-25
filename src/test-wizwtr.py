#!/usr/bin/env python3

# lektrix
# Copyright (C) 2024  Maurice (mausy5043) Hendrix
# AGPL-3.0-or-later  - see LICENSE


import asyncio
import json

from homewizard_energy import HomeWizardEnergyV1

from libzeroconf import discover as zcd

# get a HomeWizard IP
_howip = zcd.get_ip(service="_hwenergy", filter="HWE-WTR")

IP_ADDRESS = "0.0.0.0"  # nosec - B104: hardcoded_bind_all_interfaces
if _howip:
    IP_ADDRESS = _howip[0]


async def async_work():
    async with HomeWizardEnergyV1(host=IP_ADDRESS) as api:
        # blink the LED on the device
        await api.identify()

        wiz_host = api.host  # call function
        print("\nhost")
        print(wiz_host, api.host)  # function return-value and class parameter should be same

        # Get device information, like firmware version
        wiz_dev = await api.device()
        print("\ndevice")
        print(json.dumps(wiz_dev, indent=4))

        # Get measurements, like energy or water usage
        wiz_data = await api.data()
        print("\ndata")
        print(json.dumps(wiz_data, indent=4))
        print(wiz_data.total_liter_m3)

        wiz_system = await api.system()
        print("\nsystem")
        print(wiz_system)


asyncio.run(async_work())  # type ignore:[no-untyped-call]
print("\n\nNORMAL\n\n")
