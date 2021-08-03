#!/usr/bin/python3
"""
This is a simple script that allows backing up and restoring datapoints and
datapoint messages from a REST API that exposes the message format.
The API must have these endoints for this script to work:

GET/PUT /datapoint/
    To retrieve/restore the datapoint metadata.
GET/PUT /datapoint/{dp_id}/value/
    To retrieve/restore the datapoint value messages.
GET/PUT /datapoint/{dp_id}/setpoint/
    To retrieve/restore the datapoint value messages.
GET/PUT /datapoint/{dp_id}/schedule/
    To retrieve/restore the datapoint value messages.

Please note:
------------
    The value/setpoint/schedule endpoints MUST support the `timestamp__gte`
    and `timestamp__lt` query parameters that allow filtering the messages
    by data. Without these parameters the Queries will likely grow to large
    and crash the django app with every request. Even if not, the chunks
    will likely contain many copies of the existing messages.
"""
import os
import bz2
import json
import logging
import argparse
from pathlib import Path
from multiprocessing import Pool
from datetime import date, datetime, timedelta, timezone

import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s-%(funcName)s-%(levelname)s: %(message)s"
)
logger = logging.getLogger()


def date_to_timestamp(_date):
    """
    Converts a date to a timestamp in UTC.

    Arguments:
    ----------
    _date : datetime.date

    Returns:
    --------
    timestamp : int
        Milliseconds since 1.1.1970 UTC
    """
    dt = datetime(_date.year, _date.month, _date.day, tzinfo=timezone.utc)#
    timestamp = int(dt.timestamp() * 1000)
    return timestamp

def backup_datapoint_metadata(args, auth):
    """
    Fetch the metadata of all datapoints and store it in a file.

    This will store the metadata in a filename that contains the current
    date. Thus also preserving changes in metadata over time.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    auth : requests.auth object
        The auth object that is used during the request.

    Returns:
    --------
    datapoint_ids : list
        A list of datapoint IDs known to the API.
    """
    dp_metadata_url = args.target_url + "/datapoint/"
    logger.debug("Fetching datapoint metadata from: %s", dp_metadata_url)
    response = requests.get(dp_metadata_url, auth=auth)

    # Verify that the request returned OK.
    if response.status_code != 200:
        logger.error("Request failed: %s", response)
        raise RuntimeError(
            "Could not fetch datapoint metadata from url: %s" % dp_metadata_url
        )

    # Extract the metadata.
    datapoint_metadata = response.json()

    # Store the metadata on disk.
    out_fn = "datapoint_metadata_%s.json.bz2" % datetime.utcnow().date()
    out_fnp = args.data_directory / out_fn
    with open(out_fnp, "wb") as f:
        out_json = json.dumps(datapoint_metadata, indent=4)
        f.write(bz2.compress(out_json.encode()))

    # Compute the IDs which will be used later to fetch the messages.
    datapoint_ids = [dp["id"] for dp in datapoint_metadata]
    return datapoint_ids

def load_datapoint_message(cv):
    """
    The worker that loads, compresses and saves the datapoint messages for one
    day.

    Arguments:
    ----------
    cv : dict
        The chunk_var dict containing all relevant information required to load
        data for one datapoint_id, message_type and date.
        As defined in backup_datapoint_messages.
    """
    logger.debug("Fetching datapoint data from: %s", cv["dp_data_url"])
    response = requests.get(cv["dp_data_url"], auth=cv["auth"])

    # Verify that the request returned OK.
    if response.status_code != 200:
        logger.error("Request failed: %s", response)
        raise RuntimeError(
            "Could not fetch datapoint data from url: %s" % cv["dp_data_url"]
        )

    # Store the data.
    datapoint_data = response.json()
    out_json = json.dumps(datapoint_data, indent=4)
    with open(cv["out_fnp"], "wb") as f:
        f.write(bz2.compress(out_json.encode()))

def backup_datapoint_messages(args, auth, datapoint_ids):
    """
    Backup the value/setpoint/schedule messages for the requested dates.

    This creates one file (chunk) per datapoint, message_type and date.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    auth : requests.auth object
        The auth object that is used during the request.
    datapoint_ids : list
        A list of datapoint IDs for which the message should be backed up.
    """
    # Create a list all chunks to backup.
    logger.info("Computing data chunks to backup.")
    chunk_vars = []
    date = args.start_date
    skipped_chunks = 0
    while date <= args.end_date:
        # Create a folder for each day to keep the mess on HDD a bit sorted.
        out_directory = args.data_directory / str(date)
        if not out_directory.is_dir():
            os.mkdir(out_directory)

        for datapoint_id in sorted(datapoint_ids):
            for message_type in ["value", "setpoint", "schedule"]:

                # Compute filenames and full filename incl. path.
                out_fn = (
                    "dpdata_{}_{}_{}.json.bz2"
                    .format(datapoint_id, date, message_type)
                )
                out_fnp = out_directory / out_fn

                # If chunk file exists do not load again.
                if out_fnp.is_file():
                    skipped_chunks += 1
                    continue

                chunk_var = {
                    "date": date,
                    "datapoint_id": datapoint_id,
                    "message_type": message_type,
                    "ts_chunk_start": date_to_timestamp(date),
                    "ts_chunk_end": date_to_timestamp(date+timedelta(days=1)),
                    "out_fn": out_fn,
                    "out_fnp": out_fnp,
                    "auth": auth,
                }

                # This URL should request a chunk containing data for one day.
                # Well at least if the API implements the timestamp filters.
                dp_data_url = args.target_url
                dp_data_url += "/datapoint/{datapoint_id}/{message_type}/"
                dp_data_url += "?timestamp__gte={ts_chunk_start}"
                dp_data_url += "&timestamp__lt={ts_chunk_end}"
                dp_data_url = dp_data_url.format(**chunk_var)
                chunk_var["dp_data_url"] = dp_data_url

                chunk_vars.append(chunk_var)
        date += timedelta(days=1)

    chunks_to_load = len(chunk_vars)
    logger.info(
        "User requested %s chunks. %s chunks exist already. Starting download.",
        *(chunks_to_load+skipped_chunks, skipped_chunks)
    )
    # 8 Processes seems to be good compromise for decent download rates.
    pool = Pool(processes=8)
    for _ in tqdm(
        pool.imap(load_datapoint_message, chunk_vars), total=chunks_to_load
    ):
        pass
    logger.info("Finished loading %s chunks.", chunks_to_load)

def main(args):
    """
    Execute the backup or restore job.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    """
    logger.info("Starting Simple DB Backup script.")

    args.data_directory = args.data_directory.absolute()
    logger.info("Checking data directory exists: %s", args.data_directory)
    if not args.data_directory.is_dir():
        logger.error("The path specified in data directory is not a directory.")
        exit(1)

    logger.info("Checking target URL: %s", args.target_url)
    try:
        response = requests.get(args.target_url)
        assert response.status_code == 200
    except Exception:
        logger.error("Target seems to be offline. Exiting.")
        exit(2)

    # Set up authentication if required.
    if args.username is not None:
        logger.info("Using username %s for authentication", args.username)
        auth = requests.auth.HTTPBasicAuth(args.username, args.password)
    else:
        logger.debug("Using no authentication.")
        auth = None

    if args.restore:
        raise NotImplementedError("Cannot restore yet.")
    if args.backup:
        datapoint_ids = backup_datapoint_metadata(args=args, auth=auth)
        backup_datapoint_messages(
            args=args, auth=auth, datapoint_ids=datapoint_ids
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-b",
        "--backup",
        action="store_true",
        default=False,
        help="Backup the data."
    )
    group.add_argument(
        "-r",
        "--restore",
        action="store_true",
        default=False,
        help="Restore the data."
    )
    parser.add_argument(
        "-t",
        "--target-url",
        required=True,
        help=(
            "The URL of the target REST API (without trailing slash).\n"
            "E.g: http://localhost:8080"
        )
    )
    parser.add_argument(
        "-u",
        "--username",
        help=(
            "The username used for HTTP BasicAuth. If not set will connect "
            "without attempting authentication."
        )
    )
    parser.add_argument(
        "-p",
        "--password",
        help=(
            "The password for HTTP BasicAuth is only used in combination with "
            "username if username is set."
        )
    )
    parser.add_argument(
        "-s",
        "--start-date",
        required=True,
        type=date.fromisoformat,
        help=(
            "The first date (in ISO format) for which the value/schedule/"
            "setpoint messages should be backed up or restored."
        )
    )
    parser.add_argument(
        "-e",
        "--end-date",
        type=date.fromisoformat,
        default=datetime.utcnow().date() - timedelta(days=1),
        help=(
            "The last date (in ISO format) for which the value/"
            "schedule/setpoint messages should be backed up or restored. "
            "Defaults to yesterday in UTC."
        )
    )
    parser.add_argument(
        "-d",
        "--data-directory",
        type=Path,
        required=True,
        help=(
            "Path to directoy where backed up data is stored and resored data"
            "is loaded from. This directory must exist."
        )
    )
    args = parser.parse_args()
    main(args)
