#!/usr/bin/env python3

# wizwtr
# Copyright (C) 2025  Maurice (mausy5043) Hendrix
# AGPL-3.0-or-later  - see LICENSE

# https://api-documentation.homewizard.com/docs/category/api-v1

"""Common functions for use with the HomeWizard watermeter using the API/v1"""

# import asyncio
import datetime as dt
import logging
import sys
import time

import numpy as np
import pandas as pd
from homewizard_energy import HomeWizardEnergyV1

import constants
from libzeroconf import discover as zcd

LOGGER: logging.Logger = logging.getLogger(__name__)


# https://api-documentation.homewizard.com/docs/category/api-v1


class WizWTR_v1:  # pylint: disable=too-many-instance-attributes
    """Class to interact with the HomeWizard watermeter."""

    def __init__(self, debug: bool = False) -> None:  # pylint: disable=too-many-instance-attributes
        """Initialize the class."""
        # get a HomeWizard IP
        self.ip = ""
        deltat = 10.0
        while not self.ip and deltat < 300:
            _howip = zcd.get_ip(service="_hwenergy", filtr="HWE-WTR")
            if _howip:
                self.ip = _howip[0]
            else:
                LOGGER.error(f"No HomeWizard WTR found. Retrying in {deltat} seconds.")
                time.sleep(deltat)
                deltat = int(deltat * 14.142) / 10

        self.dt_format = constants.DT_FORMAT  # "%Y-%m-%d %H:%M:%S"
        # starting values
        self.water: float = 0.0
        self.list_data: list = []

        self.debug: bool = debug
        self.firstcall = True
        if debug:
            if len(LOGGER.handlers) == 0:
                LOGGER.addHandler(logging.StreamHandler(sys.stdout))
            LOGGER.level = logging.DEBUG
            LOGGER.debug("Debugging on.")
            self.telegram: list = []

    async def get_telegram(self):
        """Fetch a telegram from the serialport.

        Returns:
            (bool): valid telegram received True or False
        """
        async with HomeWizardEnergyV1(host=self.ip) as _api:
            if self.debug and self.firstcall:
                # Get device information, like firmware version
                wiz_dev = await _api.device()
                LOGGER.debug(wiz_dev)
                LOGGER.debug("")
                self.firstcall = False

            # Get measurements
            wiz_data = await _api.measurement()
            LOGGER.debug(wiz_data)
            LOGGER.debug("---")

        self.list_data.append(self._translate_telegram(wiz_data))
        LOGGER.debug(self.list_data)
        LOGGER.debug("*-*")

    def _translate_telegram(self, telegram) -> dict:
        """Translate the telegram to a dict.

        cubic meters [m3] are converted to liters.

        Returns:
            (dict): data converted to a dict.
        """

        # telegram will look something like this (we only use water data at the end):
        #
        # Data(wifi_ssid='niflheim', wifi_strength=100, smr_version=None,
        #      meter_model=None, unique_meter_id=None, active_tariff=None,
        #      total_energy_import_kwh=None, total_energy_import_t1_kwh=None,
        #      total_energy_import_t2_kwh=None, total_energy_import_t3_kwh=None,
        #      total_energy_import_t4_kwh=None, total_energy_export_kwh=None,
        #      total_energy_export_t1_kwh=None, total_energy_export_t2_kwh=None,
        #      total_energy_export_t3_kwh=None, total_energy_export_t4_kwh=None,
        #      active_power_w=None, active_power_l1_w=None, active_power_l2_w=None,
        #      active_power_l3_w=None, active_voltage_v=None, active_voltage_l1_v=None,
        #      active_voltage_l2_v=None, active_voltage_l3_v=None, active_current_a=None,
        #      active_current_l1_a=None, active_current_l2_a=None, active_current_l3_a=None,
        #      active_apparent_power_va=None, active_apparent_power_l1_va=None,
        #      active_apparent_power_l2_va=None, active_apparent_power_l3_va=None,
        #      active_reactive_power_var=None, active_reactive_power_l1_var=None,
        #      active_reactive_power_l2_var=None, active_reactive_power_l3_var=None,
        #      active_power_factor=None, active_power_factor_l1=None, active_power_factor_l2=None,
        #      active_power_factor_l3=None, active_frequency_hz=None, voltage_sag_l1_count=None,
        #      voltage_sag_l2_count=None, voltage_sag_l3_count=None, voltage_swell_l1_count=None,
        #      voltage_swell_l2_count=None, voltage_swell_l3_count=None, any_power_fail_count=None,
        #      long_power_fail_count=None, active_power_average_w=None, monthly_power_peak_w=None,
        #      monthly_power_peak_timestamp=None,
        #      total_gas_m3=None, gas_timestamp=None, gas_unique_id=None,
        #      active_liter_lpm=0, total_liter_m3=0.016,
        #      external_devices=None)

        self.water = self._calc_new_total(telegram.total_liter_m3) * 1000  # in liters

        idx_dt: dt.datetime = dt.datetime.now()
        epoch = int(idx_dt.timestamp())

        return {
            "sample_time": idx_dt.strftime(self.dt_format),
            "sample_epoch": epoch,
            "water": int(self.water),
        }

    @staticmethod
    def _calc_new_total(metered_volume: float) -> float:
        new_volume: float = metered_volume + constants.WIZ_WTR["offset"]
        for key, value in constants.WIZ_WTR["calibration"].items():
            if pd.Timestamp(key) < pd.Timestamp.now():
                new_volume += value
        return new_volume

    def compact_data(self, data) -> tuple:
        """
        Compact the data into 15-minute data

        Args:
            data (list): list of dicts containing data from the water meter

        Returns:
            (list): list of dicts containing compacted 15-minute data
        """

        def _convert_time_to_epoch(date_to_convert) -> int:
            return int(pd.Timestamp(date_to_convert).timestamp())

        def _convert_time_to_text(date_to_convert) -> str:
            return str(pd.Timestamp(date_to_convert).strftime(constants.DT_FORMAT))

        df = pd.DataFrame(data)
        df = df.set_index("sample_time")
        df.index = pd.to_datetime(df.index, format=constants.DT_FORMAT, utc=False)
        # resample to monotonic timeline
        df_out = df.resample("15min", label="right").max()
        # df_mean = df.resample("15min", label="right").mean()

        df_out["water"] = df_out["water"].astype(int)
        # recreate column 'sample_time' that was lost to the index
        df_out["sample_time"] = df_out.index.to_frame(name="sample_time")
        df_out["sample_time"] = df_out["sample_time"].apply(_convert_time_to_text)

        # recalculate 'sample_epoch'
        df_out["sample_epoch"] = df_out["sample_time"].apply(_convert_time_to_epoch)
        result_data = df_out.to_dict("records")  # list of dicts

        df = df[df["sample_epoch"] > np.max(df_out["sample_epoch"])]  # pylint: disable=E1136
        remain_data = df.to_dict("records")
        LOGGER.debug(f"Result: {result_data}")
        LOGGER.debug(f"Remain: {remain_data}\n")
        return result_data, remain_data
