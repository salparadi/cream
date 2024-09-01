import asyncio
from collections import deque
import ujson
import time
import websockets

from .app_state import AppState
from ...config import helpers
from ...config.logging import logger

log = logger(__name__)


class BlockService:
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.chain_name = self.app_state.chain_name
        self.http_uri = self.app_state.chain_data["http_uri"]
        self.node = self.app_state.chain_data["node"]
        self.redis_client = self.app_state.redis_client
        self.websocket_uri = self.app_state.chain_data["websocket_uri"]

        log.info(f"BlockService initialized with app instance at {id(self.app_state)}")

    async def get_alchemy_block_receipts(self, block_number):

        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTransactionReceipts",
            "params": [{"blockNumber": block_number}],
        }

        retries = 0  # Incrementor for retries
        max_retries = 5  # X times to retry
        initial_delay = 0.5  # Wait for X second(s) before the first try
        delay = 1  # Wait for X second(s) before the first retry

        await asyncio.sleep(initial_delay)  # Initial delay before starting the retries

        while retries < max_retries:
            async with self.app_state.http_session.post(
                self.websocket_uri, json=params
            ) as response:
                response_data = await response.json()
                if "error" not in response_data:
                    receipts = response_data.get("result", {}).get("receipts", [])
                    if receipts:
                        # Filter out receipts of type 0x7e and process the rest
                        filtered_receipts = [
                            r for r in receipts if r.get("type") != "0x7e"
                        ]
                        for receipt in filtered_receipts:
                            await self.app_state.finalized_transactions.put(receipt)
                        return
                    else:
                        log.error(f"No receipts found in the block {block_number}.")
                        return None  # Return to indicate the attempt was made but no data was found

                log.error(
                    f"Error fetching block transactions: {response_data.get('error')}"
                )

            retries += 1
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff for the delay

        log.error(
            f"Failed to fetch block transactions for {block_number} after {max_retries} retries."
        )

    async def get_infura_block_receipts(self, block_number):

        headers = {"Content-Type": "application/json"}
        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBlockByNumber",
            "params": [
                block_number,
                True,
            ],
        }

        retries = 0  # Incrementor for retries
        max_retries = 5  # X times to retry
        initial_delay = 0.5  # Wait for X second(s) before the first try
        delay = 1  # Wait for X second(s) before the first retry

        await asyncio.sleep(initial_delay)  # Initial delay before starting the retries

        while retries < max_retries:
            async with self.app_state.http_session.post(
                self.http_uri, headers=headers, json=params
            ) as response:
                response_data = await response.json()
                # print(response_data)
                if "error" not in response_data:
                    receipts = response_data.get("result", {}).get("transactions", [])
                    if receipts:
                        # Filter out receipts of type 0x7e and process the rest
                        filtered_receipts = [
                            r for r in receipts if r.get("type") != "0x7e"
                        ]
                        for receipt in filtered_receipts:
                            await self.app_state.finalized_transactions.put(receipt)
                        return
                    else:
                        log.error(f"No receipts found in the block {block_number}.")
                        return None  # Return to indicate the attempt was made but no data was found

                log.error(
                    f"Error fetching block transactions: {response_data.get('error')}"
                )

            retries += 1
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff for the delay

        log.error(
            f"Failed to fetch block transactions for {block_number} after {max_retries} retries."
        )
    
    async def get_node_block_receipts(self, block_number):
    
        headers = {"Content-Type": "application/json"}
        params = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBlockByNumber",
            "params": [
                block_number,
                True,
            ],
        }
        
        retries = 0  # Incrementor for retries
        max_retries = 5  # X times to retry
        initial_delay = 0.5  # Wait for X second(s) before the first try
        delay = 1  # Wait for X second(s) before the first retry
        
        await asyncio.sleep(initial_delay)  # Initial delay before starting the retries
        
        while retries < max_retries:
            async with self.app_state.http_session.post(
                self.http_uri, headers=headers, json=params
            ) as response:
                response_data = await response.json()
                # print(response_data)
                if "error" not in response_data:
                    receipts = response_data.get("result", {}).get("transactions", [])
                    if receipts:
                        # Filter out receipts of type 0x7e and process the rest
                        filtered_receipts = [
                            r for r in receipts if r.get("type") != "0x7e"
                        ]
                        for receipt in filtered_receipts:
                            await self.app_state.finalized_transactions.put(receipt)
                        return
                    else:
                        log.error(f"No receipts found in the block {block_number}.")
                        return None  # Return to indicate the attempt was made but no data was found
        
                log.error(
                    f"Error fetching block transactions: {response_data.get('error')}"
                )
        
            retries += 1
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff for the delay
        
        log.error(
            f"Failed to fetch block transactions for {block_number} after {max_retries} retries."
        )

    async def watch_new_blocks(self):
        """
        Watches the websocket for new blocks, updates the base fee for the last block, scans
        transactions and removes them from the pending tx queue, and prints various messages
        """

        # A rolling window of the last 100 block deltas, seeded with an initial value
        block_times = deque(
            [time.time() - self.app_state.average_blocktime],
            maxlen=100,
        )

        while True:
            try:
                async for websocket in websockets.client.connect(
                    uri=self.websocket_uri,
                    ping_timeout=None,
                    max_queue=None,
                ):
                    # reset the first block and status every time every time the watcher connects
                    self.app_state.watching_blocks = False
                    self.app_state.first_block = 0

                    await websocket.send(
                        ujson.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "eth_subscribe",
                                "params": ["newHeads"],
                            }
                        )
                    )
                    subscription_id = ujson.loads(await websocket.recv())["result"]
                    log.info(f"Subscription Active: New Blocks - {subscription_id}")
                    self.app_state.watching_blocks = True

                    while True:
                        try:
                            message = ujson.loads(await websocket.recv())
                            block = message["params"]["result"]
                            block_number = block.get("number")

                            if self.chain_name in [
                                "base",
                                "optimism",
                            ] and self.node in ["alchemy"]:
                                await self.get_alchemy_block_receipts(block_number)
                            
                            if self.chain_name in [
                                "base",
                            ] and self.node in ["node"]:
                                await self.get_node_block_receipts(block_number)

                            if self.chain_name in ["avalanche"] and self.node in [
                                "infura"
                            ]:
                                await self.get_infura_block_receipts(block_number)

                        except asyncio.exceptions.CancelledError:
                            return
                        except websockets.exceptions.WebSocketException:
                            log.exception(
                                "(watch_new_blocks) (websocket.recv) (WebSocketException)"
                            )
                            break
                        except (
                            Exception
                        ) as e:  # Using generic exception temporarily, specify your exception
                            log.exception(
                                f"(watch_new_blocks) (websocket.recv) (catch-all): {e}"
                            )
                            break

                        start = time.perf_counter()

                        self.app_state.newest_block = int(
                            message["params"]["result"]["number"], 16
                        )
                        self.app_state.newest_block_timestamp = int(
                            message["params"]["result"]["timestamp"], 16
                        )

                        block_times.append(self.app_state.newest_block_timestamp)
                        self.app_state.average_blocktime = (
                            block_times[-1] - block_times[0]
                        ) / (len(block_times) - 1)

                        if not self.app_state.first_block:
                            self.app_state.first_block = self.app_state.newest_block
                            log.info(f"First full block: {self.app_state.first_block}")

                        fee_history_result = self.app_state.w3.eth.fee_history(
                            1, "latest"
                        )["baseFeePerGas"]

                        if len(fee_history_result) == 2:
                            (
                                self.app_state.base_fee_last,
                                self.app_state.base_fee_next,
                            ) = fee_history_result
                        elif len(fee_history_result) == 1:
                            self.app_state.base_fee_last = fee_history_result[0]
                            self.app_state.base_fee_next = 0
                        else:
                            self.app_state.base_fee_last = 0
                            self.app_state.base_fee_next = 0

                        log.info(
                            f"[BLOCK #{self.app_state.newest_block}] "
                            f"[+{time.time() - self.app_state.newest_block_timestamp:.2f}s] "
                            f"[{self.app_state.base_fee_last/(10**9):.4f}/{self.app_state.base_fee_next/(10**9):.4f}]"
                        )
                        await helpers.update_redis_chain_state(
                            self.redis_client, self.app_state
                        )
                        await asyncio.sleep(0.01)

            except websockets.ConnectionClosed:
                log.exception(
                    "(watch_new_blocks) (websockets.ConnectionClosed) reconnecting...)"
                )
                continue
            except asyncio.CancelledError:
                log.info("Block watcher cancelled, shutting down")
                break
            except Exception as exc:
                log.exception(f"(watch_new_blocks) (catch-all): {exc}")
                continue
