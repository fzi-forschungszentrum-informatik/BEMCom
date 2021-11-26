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
    logger.info("Fetched metadata for %s datapoints", len(datapoint_ids))
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
        pool.imap_unordered(load_datapoint_message, chunk_vars),
        total=chunks_to_load
    ):
        pass
    logger.info("Finished loading %s chunks.", chunks_to_load)

def restore_datapoint_metadata(args, auth):
    """
    Fetches the metadata of all datapoints from file and tries to restore it.

    By design it is only possible to restore metadata to datapoints which
    have already been created as a cause of the corresponding message by
    a connector (else we would have datapoints which are detached from the
    connectors, that seems to exist but for which no connector receives and
    sends messages). As we do not know the IDs of the datapoints we want to
    restore in the DB this function restores the datapoints one after the
    other.
    For every datapoint for which has registered by a connector already sending
    a put message with the metadata of the datapoint should return 200 message
    also containing the ID of the corresponding entry in the DB. It is only
    for those datapoints possible to replay the datapoint value, setpoint and
    schedule messages as we don't have a datapoint ID (in the database) to
    PUT to.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    auth : requests.auth object
        The auth object that is used during the request.

    Returns:
    --------
    dp_id_mapping : dict
        A dict mapping from the datapoint IDs in the backup files to the
        IDs of the corresponding datapoints in the DB.
    """
    all_datapoint_metadata_fnps = args.data_directory.glob(
        "datapoint_metadata_*.json.bz2"
    )
    latest_datapoint_metadata_fnp =  sorted(all_datapoint_metadata_fnps)[-1]
    logger.info(
        "Loading datapoint metadata from: %s",
        latest_datapoint_metadata_fnp
    )
    with bz2.open(latest_datapoint_metadata_fnp, "rb") as f:
        datapoint_metadata_str = f.read().decode()
        all_datapoint_metadata = json.loads(datapoint_metadata_str)
    all_datapoint_metadata.sort(key=lambda k: k['id'])

    if not args.force_datapoint_creation:
        # First print out all connectors, that must be created by the
        # user manually before we can proceed.
        print(
            "\n"
            "Please ensure that the following connectors have been "
            "created in the BEMCom Admin page and work correctly "
            "(Datapoints are available):"
        )
    else:
        print(
            "\n"
            "The following connectors will be created if they do not "
            "exist already. Missing datapoints will be created too."
        )

    all_connectors = {dp["connector"]["name"] for dp in all_datapoint_metadata}
    for connector_name in sorted(all_connectors):
        print("-> ", connector_name)
    print("")
    logger.info("Uploading datapoint metadata.")
    if not args.yes:
        choice = input("Proceed? [y/n] ")
        if choice != "y":
            logger.info("Aborting restore by user request.")
            exit(0)

    # Updates the datapoint metadata in the API and find the datapoint id
    # used by the API, which we need later to push in the value, setpoint
    # and schedule messages.
    # This could also be done with a single PUT call, but it seems
    # safer this way.
    dp_metadata_url = args.target_url + "/datapoint/"
    dp_id_mapping = {} # Maps from ids of files to API ids.
    for datapoint_metadata in tqdm(all_datapoint_metadata):
        dp_id_file = datapoint_metadata["id"]
        datapoint_created = False

        if args.force_datapoint_creation:
            response = requests.post(
                dp_metadata_url, auth=auth, json=[datapoint_metadata]
            )
            if response.status_code == 201:
                datapoint_created = True
            else:
                logger.info(
                    "Could not create datapoint %s: %s",
                    dp_id_file,
                    response.json()
                )
                continue

        # Also trigger update if datapoint could not be created,
        # e.g. as it exists already.
        if not datapoint_created:
            response = requests.put(
                dp_metadata_url, auth=auth, json=[datapoint_metadata]
            )
            if response.status_code != 200:
                logger.warning(
                    "Error for datapint %s: %s", dp_id_file, response.json()
                )
                continue

        dp_id_api = response.json()[0]["id"]
        dp_id_mapping[dp_id_file] = dp_id_api

    logger.info(
        "Restored metadata for %s of %s datapoints.",
        len(dp_id_mapping),
        len(all_datapoint_metadata)
    )
    return dp_id_mapping

def write_datapoint_message(cv):
    """
    The worker that decompresses the datapoint messages for one
    day and triggers writing to DB by calling the PUT method.

    Arguments:
    ----------
    cv : dict
        The chunk_var dict containing all relevant information required to load
        data for one datapoint_id, message_type and date.
        As defined in restore_datapoint_messages.
    """
    logger.debug("Opening datapoint data file: %s", cv["chunk_fnp"])
    with bz2.open(cv["chunk_fnp"], "rb") as f:
        datapoint_data_str = f.read().decode()
        datapoint_data = json.loads(datapoint_data_str)

    # Skip empty datapoint_data, this happens if no data has been available
    # for that datapoint and data. But no need to restore nothing, wright?
    if not datapoint_data:
        # This is similar to the output of response.json() below.
        {'msgs_created': 0, 'msgs_updated': 0}

    # Try to parse data, i.e. bools and floats to allow storing them
    # not as strings. New versions of the database should have generated
    # the data correctly wright away, but this is a backfix for older data.
    for msg in datapoint_data:
        if "value" in msg:
            if  msg["value"] in [None, "null"]:
                value_native = None
            elif msg["value"] in ["True", "true", "TRUE", True]:
                value_native = True
            elif msg["value"] in ["False", "false", "FALSE", False]:
                value_native = False
            else:
                try:
                    value_native = float(msg["value"])
                except ValueError:
                    # This must be a string then, as BEMCOM only knows the
                    # datatypes string, bool and float.
                    value_native = msg["value"]
            msg["value"] = json.dumps(value_native)
    logger.debug("Pushing datapoint data to: %s", cv["dp_data_url"])
    response = requests.put(
        cv["dp_data_url"], auth=cv["auth"], json=datapoint_data
    )
    # Verify that the request returned OK.
    if response.status_code != 200:
        logger.error(
            "Request failed (%s): %s", response.status_code, response.json()
        )
        raise RuntimeError(
            "Could not write datapoint data to url: %s" % cv["dp_data_url"]
        )

    return response.json()

def restore_datapoint_messages(args, auth, dp_id_mapping):
    """
    Restore the value/setpoint/schedule messages for the requested dates.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    auth : requests.auth object
        The auth object that is used during the request.
    dp_id_mapping : dict
        A dict mapping from the datapoint IDs in the backup files to the
        IDs of the corresponding datapoints in the DB.
    """
    if not args.yes:
        choice = input(
            "\nWould you like to restore value/setpoint/schedule messages "
            "for %s datapoints?\n[y/n] " % len(dp_id_mapping)
        )
        if choice != "y":
            logger.info("Aborting restore by user request.")
            exit(0)
    else:
        logger.info(
            "Restoring value/setpoint/schedule messages for %s datapoints",
            len(dp_id_mapping)
        )

    # Find all chunks relevant for the selected dates and datapoints.
    # Iterate over dates first as this supports the way the data is stored
    # in tables in timescaleDB.
    chunk_vars = []
    date = args.start_date
    while date <= args.end_date:
        out_directory = args.data_directory / str(date)
        for dp_id_file in dp_id_mapping:
            for message_type in ["value", "setpoint", "schedule"]:
                # Compute filenames and full filename incl. path.
                # Also check whether file exists, as for some datapoints
                # not the full history may exist (e.g. datapoint added later).
                chunk_fn = (
                    "dpdata_{}_{}_{}.json.bz2"
                    .format(dp_id_file, date, message_type)
                )
                chunk_fnp = out_directory / chunk_fn
                if chunk_fnp.is_file():
                    dp_id_api = dp_id_mapping[dp_id_file]
                    dp_data_url = args.target_url
                    dp_data_url += "/datapoint/{}/{}/"
                    dp_data_url = dp_data_url.format(dp_id_api, message_type)
                    chunk_var = {
                        "chunk_fnp": chunk_fnp,
                        "dp_data_url": dp_data_url,
                        "auth": auth,

                    }
                    chunk_vars.append(chunk_var)
        date += timedelta(days=1)

    logger.info("Starting to process %s chunks", len(chunk_vars))
    # Django-API (CPU processing) is the main bottleneck here, there is
    # hence no point in parallelizing more.
    pool = Pool(processes=2)
    msgs_created_total = 0
    msgs_updated_total = 0
    for msg_stats in tqdm(
        pool.imap_unordered(write_datapoint_message, chunk_vars),
        total=len(chunk_vars)
    ):
        msgs_created_total += msg_stats["msgs_created"]
        msgs_updated_total += msg_stats["msgs_updated"]

    logger.info("Finished loading %s chunks.", len(chunk_vars))
    logger.info(
        "Created %s and updated %s messages in total.",
        msgs_created_total,
        msgs_updated_total
    )

def main(args):
    """
    Execute the backup or restore job.

    Arguments:
    ----------
    args : argparse.Namespace
        As defined at the end of the script.
    """
    logger.info("Starting Simple DB Backup script.")
    logger.info("Start date: %s End date: %s", args.start_date, args.end_date)

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
        dp_id_mapping = restore_datapoint_metadata(args=args, auth=auth)
        restore_datapoint_messages(
           args=args, auth=auth, dp_id_mapping=dp_id_mapping
        )

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
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help=(
            "Always answer yes while restoring. This is fine if one has"
            "has ensured that connectors and datapoints exist before running "
            "the script."
        )
    )
    parser.add_argument(
        "-f",
        "--force-datapoint-creation",
        action="store_true",
        help=(
            "Force creation of datapoints and connectors. This is potentially"
            "dangerous. You might end up with datapoints about which the "
            "corresponding connector doesn't know. These datapoints will "
            "not receive data or nor will it be possible to send value "
            "messages to actuator datapoints."
        )
    )
    args = parser.parse_args()
    main(args)
