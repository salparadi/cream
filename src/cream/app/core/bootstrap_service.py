import aiohttp
import redis.asyncio as redis
import time
import web3

from cream_chains import chains

from .app_state import AppState
from ...config.logger import logger

log = logger(__name__)


class BootstrapService:
    def __init__(self, app_state: AppState, chain_name: str):
        self.chain_name = chain_name
        self.chain_info = chains.get(chain_name)

        if not self.chain_info:
            log.error(
                f"Invalid chain name: {chain_name}. Please specify a valid chain from the supported list."
            )
            raise ValueError(f"Invalid chain name: {chain_name}")

        self.app_state = app_state
        self.app_state.chain_name = chain_name
        self.app_state.chain_info = self.chain_info
        self.app_state.node = self.chain_info.get("node")
        self.app_state.http_uri = self.chain_info.get("http_uri")
        self.app_state.websocket_uri = self.chain_info.get("websocket_uri")

        log.info(
            f"BootstrapService initialized with app instance at {id(self.app_state)}"
        )

    async def start(self):
        try:
            w3 = web3.Web3(web3.WebsocketProvider(self.app_state.websocket_uri))
            chain_id = w3.eth.chain_id
            newest_block = w3.eth.block_number

            self.app_state.w3 = w3

            self.app_state.redis_client = redis.Redis(host="localhost", port=6379, db=0)
            await self.app_state.redis_client.flushdb()

            self.app_state.http_session = aiohttp.ClientSession()

            self.app_state.chain_id = chain_id
            self.app_state.newest_block = newest_block
            self.app_state.newest_block_timestamp = int(time.time())

            self.app_state.live = True

            log.info(
                f"Connected to {self.chain_name} (Chain ID: {chain_id}) at Block {newest_block}"
            )

        except Exception as e:
            log.error(f"Error connecting to network: {e}")
