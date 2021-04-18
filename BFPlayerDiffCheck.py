#!/usr/bin/env python3
"""
Copyright gitlab.com/hedius github.com/hedius

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import asyncio
from argparse import ArgumentParser
from BFDataGatherer.Gatherer import Gatherer


def main():
    parser = ArgumentParser(
        description='Simple tool for logging different player counts of '
                    'battlefield servers. Writes data to stdout + to a csv.'
    )
    parser.add_argument('-v', '--version',
                        choices=['bf3', 'bf4'],
                        required=True,
                        dest='game',
                        help='Game version.')
    parser.add_argument('-g', '--guid',
                        required=True,
                        dest='guid',
                        help='Server GUID')
    parser.add_argument('-w', '--csv-file',
                        dest='csv_file',
                        default='server_log.csv',
                        help='Optional path to csv log. Default '
                             'server_log.csv')
    parser.add_argument('-i', '--interval',
                        dest='interval',
                        default=20,
                        help='Logging interval in seconds. Min 10s.')
    parser.add_argument('--webhook',
                        dest='webhook',
                        help='Discord webhook for unranked logging.')
    args = parser.parse_args()

    try:
        interval = int(args.interval)
    except TypeError:
        interval = 20

    logging.basicConfig(level=logging.INFO)

    gatherer = Gatherer(args.guid, interval, args.game)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(gatherer.monitor(args.csv_file, args.webhook))
    finally:
        loop.close()


if __name__ == '__main__':
    main()
