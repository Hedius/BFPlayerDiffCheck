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
import csv
import os
import asyncio
import logging
from datetime import datetime
from typing import Tuple

import aiohttp
from discord_webhook import DiscordWebhook, DiscordEmbed

headers = {
    'User-Agent': 'BFPlayerDiffCheck by Hedius',
    'Accept-Encoding': 'gzip, deflate'
}


class Gatherer:
    """
    Basic gatherer for getting different player count values from
    Battlelog.
    """
    GAME_BF3 = 'bf3'
    GAME_BF4 = 'bf4'

    def __init__(self, guid: str, request_interval: int, game: str):
        """
        Basic gatherer for getting different player count values from
        Battlelog.
        :param guid: server guid
        :param request_interval: interval between requests (min 10s)
        :param game: bf4 or bf3
        """
        self._guid = guid

        self._request_interval = (request_interval
                                  if request_interval >= 10
                                  else 10)

        self._game = game.lower()
        if self._game not in (self.GAME_BF4, self.GAME_BF3):
            logging.critical('Unsupported game %s!', game)
            raise AttributeError(f'Unsupported game {game}')

        self._url_profile = (
            f'http://battlelog.battlefield.com/{self._game}/servers/show/pc/'
            f'{guid}?json=1'
        )

        self._url_keeper = f'https://keeper.battlelog.com/snapshot/{guid}'

        self._name = "Unknown"
        self._player_count = 0
        self._keeper_count = 0
        self._true_player_count = 0
        self._max_slots = 0
        self._queue = 0
        self._ranked = None
        self._ranked_previous = None

        self._lock = asyncio.Lock()

    async def get_counts_keeper(self, session: aiohttp.ClientSession) -> int:
        """
        Pull data from keeper.
        :param session: async session
        :return: cur player count from keeper
        """
        player_count = 0
        if self._game != self.GAME_BF4:
            async with self._lock:
                self._keeper_count = 0
            return 0

        try:
            async with session.get(self._url_keeper, headers=headers) as r:
                data = await r.json()
                snapshot = data['snapshot']
                for team in snapshot['teamInfo']:
                    player_count += len(snapshot['teamInfo'][team]['players'])
        except (TypeError, aiohttp.ClientError, aiohttp.ContentTypeError):
            logging.warning(
                f'Keeper request: Server with guid {self._guid} is offline.')

        async with self._lock:
            self._keeper_count = player_count
        return player_count

    async def get_counts_profile(self, session: aiohttp.ClientSession)\
            -> Tuple[int, int, int, int, bool]:
        """
        Pull data from server profile
        :param session: async session
        :return: 5-Tuple: player_count, max_slots, queue, true_player_count,
            ranked
        """
        player_count = max_slots = queue = true_player_count = -1
        ranked = self._ranked
        name = 'N/A'
        try:
            async with session.get(self._url_profile, headers=headers) as r:
                data = await r.json()
                if data['type'] == 'success':
                    name = data['message']['SERVER_INFO']['name']
                    slots = data['message']['SERVER_INFO']['slots']
                    player_count = slots['2']['current']
                    max_slots = slots['2']['max']
                    queue = slots['1']['current']
                    ranked = data['message']['SERVER_INFO']['serverType'] != 4
                    true_player_count = len(data['message']['SERVER_PLAYERS'])

        except (TypeError, aiohttp.ClientError, aiohttp.ContentTypeError):
            logging.warning(
                f'Profile request: Server with guid {self._guid} is offline.')

        async with self._lock:
            self._name = name
            self._player_count = player_count
            self._max_slots = max_slots
            self._queue = queue
            self._true_player_count = true_player_count
            self._ranked = ranked
            if self._ranked_previous is None:
                self._ranked_previous = ranked
        return player_count, max_slots, queue, true_player_count, ranked

    async def _log_results(self, log_file):
        def log_stdout():
            logging.info(
                '%s Players: %s, TrueCountKeeper: %s, TrueCountProfile: '
                '%s, MaxCount: %s, Queue: %s, DiffKeeper: %s, '
                'DiffProfile: %s, Ranked: %s',
                time, player_count, keeper_count, true_player_count,
                max_slots, queue, diff_keeper, diff_profile, ranked)

        def log_csv():
            header = ['date_time', 'players', 'true_count_keeper',
                      'true_count_profile', 'max_count', 'queue',
                      'diff_keeper',
                      'diff_profile', 'ranked']
            file_exists = os.path.exists(log_file)
            data = {
                'date_time': time,
                'players': player_count,
                'true_count_keeper': keeper_count,
                'true_count_profile': true_player_count,
                'max_count': max_slots,
                'queue': queue,
                'diff_keeper': diff_keeper,
                'diff_profile': diff_profile,
                'ranked': ranked
            }
            with open(log_file, mode='a') as fp:
                writer = csv.DictWriter(fp, header)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(data)

        # "main" body of function
        async with self._lock:
            keeper_count = self._keeper_count
            player_count = self._player_count
            max_slots = self._max_slots
            queue = self._queue
            true_player_count = self._true_player_count
            ranked = self._ranked

        diff_keeper = keeper_count - player_count
        diff_profile = true_player_count - player_count

        if self._game != self.GAME_BF4:
            keeper_count = '?'
            diff_keeper = '?'

        time = datetime.now().replace(microsecond=0)
        log_stdout()
        log_csv()

    async def check_unranked(self, webhook_url):
        async with self._lock:
            if self._ranked == self._ranked_previous:
                return False
            self._ranked_previous = self._ranked

        embed = DiscordEmbed(
            title=f'SERVER IS {"RANKED" if self._ranked else "UNRANKED"}',
            description=(
                f'**{self._name}** is '
                'RANKED' if self._ranked else 'UNRANKED'
            ),
            color='0fef00' if self._ranked else 'f72731',
            timestamp=str(datetime.utcnow())
        )
        embed.add_embed_field(name='Name', value=self._name, inline=False),
        embed.add_embed_field(name='Ranked', value=str(self._ranked))

        webhook = DiscordWebhook(webhook_url)
        webhook.add_embed(embed)
        webhook.execute()

    async def monitor(self, log_file: str, webhook=None):
        """
        Monitor the given server and display the status stout.
        Also write the log data to a csv.
        :param log_file: path to file
        :param webhook: discord_webhook for unranked monitoring
        """
        async def monitor_task():
            """asyncio task for fetching new data from battlelog"""
            async with aiohttp.ClientSession(trust_env=True) as session:
                while True:
                    await self.get_counts_keeper(session)
                    await self.get_counts_profile(session)
                    await self._log_results(log_file)
                    await asyncio.sleep(self._request_interval)

        async def unranked_announcer_task():
            while True:
                await self.check_unranked(webhook)
                await asyncio.sleep(30)

        task_gatherer = asyncio.create_task(monitor_task())
        if webhook:
            task_unranked = asyncio.create_task(unranked_announcer_task())
            await task_unranked
        await task_gatherer
