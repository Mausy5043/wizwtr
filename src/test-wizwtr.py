#!/usr/bin/env python3

# wizwtr
# Copyright (C) 2025  Maurice (mausy5043) Hendrix
# AGPL-3.0-or-later  - see LICENSE


import asyncio

from homewizard_energy import HomeWizardEnergyV1

from libzeroconf import discover as zcd

# get a HomeWizard IP
_howip = zcd.get_ip(service="_hwenergy", filtr="HWE-WTR")

IP_ADDRESS = "0.0.0.0"  # nosec - B104: hardcoded_bind_all_interfaces
if _howip:
    IP_ADDRESS = _howip[0]


async def async_work():
    try:
        async with HomeWizardEnergyV1(host=IP_ADDRESS) as api:
            # blink the LED on the device
            await api.identify()

            wiz_host = api.host  # call function
            print("\nhost")
            print(wiz_host, api.host)  # function return-value and class parameter should be same

            # Get device information, like firmware version
            wiz_dev = await api.device()
            print("\ndevice")
            print(wiz_dev)

            # Get measurements, like energy or water usage
            wiz_data = await api.measurement()
            print("\ndata")
            print(wiz_data)
            print(f"\n{wiz_data.total_liter_m3} m3")

            wiz_system = await api.system()
            print("\nsystem")
            print(wiz_system)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(async_work())
    print("\n\nNORMAL\n\n")
