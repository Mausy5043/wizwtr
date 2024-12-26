#!/usr/bin/env python3

# lektrix
# Copyright (C) 2024  Maurice (mausy5043) Hendrix
# AGPL-3.0-or-later  - see LICENSE

"""Create trendbargraphs of the data for various periods.
Using myenergi data
"""

# pylint: disable=C0413
import argparse
import sqlite3 as s3

# import warnings
from datetime import datetime as dt

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

import constants

# FutureWarning: The default value of numeric_only in DataFrameGroupBy.sum is deprecated.
# In a future version, numeric_only will default to False. Either specify numeric_only or
# select only columns which should be valid for the function.
#   df = df.resample(f"{aggregation}", label=lbl).sum()
# warnings.simplefilter(action="ignore", category=FutureWarning)


DATABASE = constants.TREND["database"]
TABLE_MAINS = constants.WIZ_WTR["sql_table"]

# fmt: off
parser = argparse.ArgumentParser(description="Create a trendgraph")
parser.add_argument("--hours", "-hr",
                    type=int,
                    help="create hour-trend for last <HOURS> hours",
                    )
parser.add_argument("--days", "-d",
                    type=int,
                    help="create day-trend for last <DAYS> days"
                    )
parser.add_argument("--months", "-m",
                    type=int,
                    help="number of months of data to use for the graph",
                    )
parser.add_argument("--years", "-y",
                    type=int,
                    help="number of months of data to use for the graph",
                    )
parser.add_argument("--edate", "-e",
                    type=str,
                    help="date of last day of the graph (default: now)",
                    )
parser_group = parser.add_mutually_exclusive_group(required=False)
parser_group.add_argument("--debug",
                          action="store_true",
                          help="start in debugging mode"
                          )
OPTION = parser.parse_args()
# fmt: on

DEBUG = False
EDATETIME = "'now'"


def fetch_data(hours_to_fetch=48, aggregation="W") -> dict:
    """Query the database to fetch the requested data

    Args:
        hours_to_fetch (int): hours of data to retrieve
        aggregation (str): pandas resample rule

    Returns:
        dict with dataframes containing mains and production data
    """
    if DEBUG:
        print(f"\nRequest {hours_to_fetch} hours of mains data")
        print("\n*** fetching mains data ***")

    where_condition = (
        f" ( sample_time >= datetime({EDATETIME}, '-{hours_to_fetch + 1} hours')"
        f" AND sample_time <= datetime({EDATETIME}, '+2 hours') )"
    )
    group_condition = ""
    # if aggregation == 'H':
    #     group_condition = "GROUP BY strftime('%d %H', sample_time)"
    s3_query: str = (
        f"SELECT * "  # nosec B608
        f"FROM {TABLE_MAINS} "
        f"WHERE {where_condition} {group_condition};"
    )
    if DEBUG:
        print(s3_query)

    # Get the data
    with s3.connect(DATABASE) as con:
        df = pd.read_sql_query(
            s3_query, con, parse_dates=["sample_time"], index_col="sample_epoch"
        )

    if DEBUG:
        print("o  database totaliser data")
        print(df.to_markdown(floatfmt=".3f"))   # requires `tabulate` package

    # Pre-processing
    # drop sample_time separately!
    df.drop("sample_time", axis=1, inplace=True, errors="ignore")

    for c in df.columns:
        if c not in ["sample_time"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # df.index = pd.to_datetime(df.index, unit='s')
    #              .tz_localize("UTC")
    #              .tz_convert("Europe/Amsterdam")
    df.index = pd.to_datetime(df.index, unit="s")  # noqa

    # Convert totalizers to first-order differences
    df = df.diff().dropna()

    # resample to monotonic timeline
    df = df.resample(f"{aggregation}").sum()

    # drop first row as it will usually not contain valid or complete data
    if aggregation == "h":
        df = df.iloc[1:, :]

    if DEBUG:
        print("o  database totaliser data pre-processed")
        print(df.to_markdown(floatfmt=".3f"))   # requires `tabulate` package

    df_wtr = df.sort_index(axis=1)
    if DEBUG:
        print("\n\n ** mains data for plotting  **")
        print(df_wtr.to_markdown(floatfmt=".3f"))   # requires `tabulate` package

    data_dict = {}
    data_dict["mains"] = df_wtr
    return data_dict


def plot_graph(
    output_file, data_dict, plot_title, show_data: bool = False, locatorformat: list = []
) -> None:
    """Plot the data in a chart.

    Args:
        output_file (str): path & filestub of the resulting plot.
                           The parametername will be appended as will the
                           extension .png.
        data_dict (dict): dict containing the datasets to be plotted
        plot_title (str): text for the title to be placed above the plot
        show_data (bool): whether to show numerical values in the plot.
        locatorformat (list): formatting information for xticks

    Returns: nothing
    """
    if not locatorformat:
        locatorformat = ["hour", "%d-%m %Hh"]
    if DEBUG:
        print("\n\n*** PLOTTING ***")
    for parameter in data_dict:
        data_frame = data_dict[parameter]  # type: pd.DataFrame
        # if DEBUG:
        #     print(parameter)
        #     print(data_frame)
        mjr_ticks = int(len(data_frame.index) / 30)
        if mjr_ticks <= 0:
            mjr_ticks = 1
        ticklabels = [""] * len(data_frame.index)
        ticklabels[::mjr_ticks] = [
            item.strftime(locatorformat[1]) for item in data_frame.index[::mjr_ticks]
        ]
        if DEBUG:
            print(ticklabels)
        if len(data_frame.index) == 0:
            if DEBUG:
                print("No data.")
        else:
            fig_x = 20
            fig_y = 7.5
            fig_fontsize = 13
            ahpla = 0.7

            # create a line plot
            plt.rc("font", size=fig_fontsize)
            ax1 = data_frame.plot(
                kind="bar",
                stacked=True,
                width=0.9,
                figsize=(fig_x, fig_y),
                color=["blue", "red", "seagreen", "lightgreen", "salmon"],
            )
            # linewidth and alpha need to be set separately
            for _, a in enumerate(ax1.lines):
                plt.setp(a, alpha=ahpla, linewidth=1, linestyle=" ")
            if show_data:
                x_offset = -0.1
                for p in ax1.patches:
                    b = p.get_bbox()  # type: ignore[attr-defined]
                    val = f"{b.y1 - b.y0:{constants.FLOAT_FMT}}"
                    ax1.annotate(
                        val,
                        ((b.x0 + b.x1) / 2 + x_offset, b.y0 + 0.5 * (b.y1 - b.y0)),
                        rotation=30,
                    )
            ax1.set_ylabel(parameter)
            ax1.legend(loc="upper left", ncol=8, framealpha=0.2)
            ax1.set_xlabel("Datetime")
            ax1.grid(which="major", axis="y", color="k", linestyle="--", linewidth=0.5)
            ax1.xaxis.set_major_formatter(mticker.FixedFormatter(ticklabels))
            plt.gcf().autofmt_xdate()
            plt.title(f"{parameter} {plot_title}")
            plt.tight_layout()
            plt.savefig(fname=f"{output_file}_{parameter}.png", format="png")
            if DEBUG:
                print(f" --> {output_file}_{parameter}.png\n")


def main(opt) -> None:
    """
    This is the main loop
    """
    if opt.hours:
        plot_graph(
            constants.TREND["hour_graph"],
            fetch_data(hours_to_fetch=opt.hours, aggregation="h"),
            f" trend afgelopen uren ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            locatorformat=["hour", "%d-%m %Hh"],
        )
    if opt.days:
        plot_graph(
            constants.TREND["day_graph"],
            fetch_data(hours_to_fetch=opt.days * 24, aggregation="D"),
            f" trend afgelopen dagen ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            locatorformat=["day", "%Y-%m-%d"],
        )
    if opt.months:
        plot_graph(
            constants.TREND["month_graph"],
            fetch_data(hours_to_fetch=opt.months * 31 * 24, aggregation="ME"),
            f" trend afgelopen maanden ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            show_data=False,
            locatorformat=["month", "%Y-%m"],
        )
    if opt.years:
        plot_graph(
            constants.TREND["year_graph"],
            fetch_data(hours_to_fetch=opt.years * 366 * 24, aggregation="YE"),
            f" trend afgelopen jaren ({dt.now().strftime('%d-%m-%Y %H:%M:%S')})",
            show_data=True,
            locatorformat=["year", "%Y"],
        )


if __name__ == "__main__":
    if OPTION.hours == 0:
        OPTION.hours = 80
    if OPTION.days == 0:
        OPTION.days = 80
    if OPTION.months == 0:
        OPTION.months = 6 * 12 + dt.now().month
    if OPTION.years == 0:
        OPTION.years = 10
    if OPTION.edate:
        print("NOT NOW")
        EDATETIME = f"'{OPTION.edate}'"

    if OPTION.debug:
        print(OPTION)
        DEBUG = True
        print("DEBUG-mode started")
    main(OPTION)
