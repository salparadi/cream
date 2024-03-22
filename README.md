# Overview
CREAM is a python module to watch new blocks, events, and transactions on EVM chains. Much of this work has been inspired by [BowTiedDevil](https://twitter.com/BowTiedDevil). Some of the LP/Liquidity/Arb path builders are directly based on his work. Go check out his stack [Degen Code](https://www.degencode.com/) for great insight into blockchain work with Python and Vyper. TY Devil!

## Prerequisites
- Python version 3.10 or newer.
- Redis ([website](https://redis.io))

## Dependencies
- aiohttp ([pypi](https://pypi.org/project/aiohttp/): Used to communicate with RPCs. It should be auto installed when you install this
- degenbot ([pypi](https://pypi.org/project/degenbot/) | [github](https://github.com/BowTiedDevil/degenbot)): It should be auto installed when you install this and will install it's own set of dependencies, which this app relies on in turn.
- fastapi ([pypi](https://pypi.org/project/degenbot/)): Used for a simple API server to expose chain details. It should be auto installed when you install this.
- redis ([pypi](https://pypi.org/project/degenbot/)): Used to interact with a redis server. It should be auto installed when you install this.
- ujson ([pypi](https://pypi.org/project/degenbot/)): Used to parse JSON. It should be auto installed when you install this.
- uvicorn ([pypi](https://pypi.org/project/degenbot/)): Used alongside the FastAPI server. It should be auto installed when you install this.
- web3 ([pypi](https://pypi.org/project/web3/)): Used for a bunch of stuff! It should be auto installed when you install this.

## CREAM dependencies
- CREAMchains [github](https://github.com/salparadi/cream-chains): You'll need this installed to have access to the chain data (things like factories, routers, rpcs, etc). This isn't a package yet, so you need to `git clone` it and install it as an editable installation in a separate folder.

## Installation
At the moment the only way to install is from source. Use `git clone` to create a local copy of this repo, then install with `pip install -e /path/to/repo`. This creates an editable installation that can be imported into a script or Python REPL using `import cream`.

# How the hell do I use this?
You'll need to do a bit of legwork to get your environment set up. You'll want to get redis working so the watchers can pass messages into it for consumption by whatever bot you build.

To start watching a chain just run `cream chain_name`. At the moment the supported chains are:

- **arbitrum** (*alchemy* / *local node*)
- **avalanche** (*infura* / *local node*)
- **base** (*alchemy* / *local node*)
- **ethereum** (*alchemy* / *local node*)
- **optimism** (*alchemy* / *local node*)
- **polygon** (*alchemy* / *local node*)

# Redis
Once you have a redis server running, this tool will publish messages to these channels

 - `cream_events`
 - `cream_pending_transactions`
 - `cream_finalized_transactions`

Depending on the chain, either pending or finalized transactions channels are used. Base and Optimism don't have pending transactions so you can only see them after they are confirmed in a block. The rest should work with pending transactions. Arbitrum uses the sequencer. This will certainly be updated during development.

The app expects Redis to be local on port 6379 when you run the watcher. You can alter the host/port as needed in `config/constants.py`. 

# FastAPI
There is an api server that starts up on port 8000 when you run the watcher. You can alter the host/port in `config/constants.py`. There is only one endpoint at the moment, there may be more in the future. They return JSON.

 - http://FASTAPI_HOST:FASTAPI_PORT/app/: Gives basic details on the chain and the status.

# Shell Constants
You'll need to add a few things to your `.bashrc/.zshrc` to ensure the connections can be made. I highly recommend using Alchemy if you don't have a local node. If you do, just configure things for that. See the shell-example.txt file for how to add those. The other CREAM tools rely on [Ape](https://github.com/ApeWorX/ape) for a lot of things so you'll see some ape-specific stuff in various files. This project doesn't need Ape, but you'll need to set that stuff up if you use it.

# Work in progress
This is undoubtedly busted in several ways, but I'll be working on it for personal use so it should get refined.