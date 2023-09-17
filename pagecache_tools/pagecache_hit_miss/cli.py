import argparse
import logging
import os
import signal
import sys

import daemon
from pid import PidFile

from pagecache_tools.pagecache_hit_miss.configure_logging import configure_logging
from pagecache_tools.pagecache_hit_miss.pagecache_hit_miss import PageCacheHitMiss

logger = logging.getLogger(__name__)


def parseargs():
    parser = argparse.ArgumentParser(description="PageCache Hit/Miss")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=5,
        help="Sets the interval to get the missed/hit values and calculate the avg.",
        required=False,
    )
    parser.add_argument(
        "--daemon",
        required=False,
        default=False,
        action="store_true",
        help="Execute the program in daemon mode.",
    )
    parser.add_argument(
        "--send-metrics-to-dogstatsd",
        required=False,
        default=False,
        action="store_true",
        help="Send metrics to local DogStatsD https://docs.datadoghq.com/developers/dogstatsd/",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["INFO", "DEBUG"],
        default="INFO",
        help="Sets the log level",
        required=False,
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="/var/log/pagecache_hit_miss.log",
        help="Sets the log file.",
        required=False,
    )
    return parser.parse_args()


def signal_term_handler(signal, frame):
    logger.info(
        "Terminating PageCache Hit/Miss service ({} mode)...".format(
            os.environ["EXECUTION_MODE"]
        )
    )
    logging.shutdown()
    sys.exit(0)


def load_daemon_mode(args, log_file_fd):
    context = daemon.DaemonContext(
        umask=0o002,
        pidfile=PidFile(pidname="/var/run/pagecache_hit_miss.pid"),
    )
    context.files_preserve = [log_file_fd]
    context.signal_map = {signal.SIGTERM: signal_term_handler}

    with context:
        pagecache_hit_miss = PageCacheHitMiss(
            args.interval_seconds,
            args.log_file,
            args.send_metrics_to_dogstatsd,
        )
        pagecache_hit_miss.run()


def load_script_mode(args):
    pagecache_hit_miss = PageCacheHitMiss(
        args.interval_seconds,
        args.log_file,
        args.send_metrics_to_dogstatsd,
    )

    signal.signal(signal.SIGTERM, signal_term_handler)
    signal.signal(signal.SIGINT, signal_term_handler)
    pagecache_hit_miss.run()


def main():
    args = parseargs()
    log_file_fd = configure_logging(args.log_level, args.log_file)

    if args.daemon:
        os.environ["EXECUTION_MODE"] = "daemon"
        logger.info("Starting PageCache Hit/Miss service as daemon mode...")
        load_daemon_mode(args, log_file_fd)
    else:
        os.environ["EXECUTION_MODE"] = "script"
        logger.info("Starting PageCache Hit/Miss as script mode...")
        load_script_mode(args)
