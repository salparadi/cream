import argparse
import asyncio
import signal
import sys
import threading

from .app.api.api_service import ApiService
from .app.core.app_state import app_state
from .app.core.block_service import BlockService
from .app.core.bootstrap_service import BootstrapService
from .app.core.event_service import EventService
from .app.core.transaction_service import TransactionService


async def main(chain_name):

    # Get the event loo
    loop = asyncio.get_event_loop()

    # Bootstrap the app by connecting to the network and loading chain info
    bootstrap_service = BootstrapService(app_state, chain_name)
    await bootstrap_service.start()

    # Initialize services
    api_service = ApiService(app_state)
    block_service = BlockService(app_state)
    event_service = EventService(app_state)
    transaction_service = TransactionService(app_state)

    # Run the API in its own thread
    api_thread = threading.Thread(target=api_service.start_api, daemon=True)
    api_thread.start()

    # Always run these tasks
    tasks = [
        block_service.watch_new_blocks(),
        event_service.watch_events(),
    ]

    # Conditionally choose which transaction tasks to run based on the chain/node combo
    if (
        app_state.node == "alchemy" and app_state.chain_name in ["base", "optimism"]
    ) or (app_state.node == "infura" and app_state.chain_name in ["avalanche"]):
        tasks.append(transaction_service.process_finalized_transactions())
    else:
        tasks.append(transaction_service.watch_transactions())
        tasks.append(transaction_service.process_pending_transactions())

    # Gather all tasks to run
    all_tasks = asyncio.gather(*tasks)

    # Set up graceful shutdown
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            s,
            lambda: asyncio.create_task(
                shutdown(loop, all_tasks, api_service, app_state)
            ),
        )

    # Run the tasks
    try:
        await all_tasks
    except asyncio.CancelledError:
        pass

    api_thread.join()


def run():
    # Get the chain name from the command line
    parser = argparse.ArgumentParser(
        description="Run the block/transaction watcher for a specified chain."
    )
    parser.add_argument(
        "chain", help="The chain name to load/use (ethereum/arbitrum/etc.)"
    )
    args = parser.parse_args()

    asyncio.run(main(args.chain))


async def shutdown(loop, all_tasks, api_service, app_state):
    print("Received exit signal, shutting down...")
    all_tasks.cancel()  # Cancel all running tasks

    # Stop the API
    await api_service.stop_api()

    # Close the aiohttp ClientSession
    if app_state.http_session:
        await app_state.http_session.close()

    # Close the Redis connection
    if app_state.redis_client:
        await app_state.redis_client.aclose()

    # Wait for all tasks to be cancelled
    await asyncio.sleep(3)

    # Stop the event loop
    loop.stop()


if __name__ == "__main__":
    # Get the chain name from the command line
    parser = argparse.ArgumentParser(
        description="Run the block/transaction watcher for a specified chain."
    )
    parser.add_argument(
        "chain", help="The chain name to load/use (ethereum/arbitrum/etc.)"
    )
    args = parser.parse_args()

    asyncio.run(main(args.chain))
