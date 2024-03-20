# Overview
CREAM is a python module to watch new blocks, events, and transactions on EVM chains. Much of this work has been inspired by [BowTiedDevil](https://twitter.com/BowTiedDevil). Some of the LP/Liquidity/Arb path builders are directly based on his work. Go check out his stack [Degen Code](https://www.degencode.com/) for great insight into blockchain work with Python and Vyper. TY Devil!

## Prerequisites
Python version 3.10 or newer.

## Dependencies
You need [degenbot](https://github.com/BowTiedDevil/degenbot). It should be auto installed when you install this. The rest of the things you need should install when you install this package. If they don't, just install them from pip and I'll get them added to the dependencies.

## Installation
At the moment the only way to install is from source

### From Source
Use `git clone` to create a local copy of this repo, then install with `pip install -e /path/to/repo`. This creates an editable installation that can be imported into a script or Python REPL using `import cream`.

# How the hell do I use this?
You'll need to do a bit of legwork to get your environment set up. You'll want to get redis working so the watchers can pass messages into it for consumption by whatever bot you build.

To start watching a chain just run `cream chain_name`. At the moment the supported chains are:

 - arbitrum
 - avalanche
 - base
 - ethereum
 - optimism
 - polygon

# Redis
Once you have a redis server running, this tool will publish messages to these channels

 - cream_events
 - cream_pending_transactions
 - cream_finalized_transactions

Depending on the chain, either pending or finalized transactions channels are used. Base and Optimism don't have pending transactions so you can only see them after they are confirmed in a block. The rest should work with pending transactions. Arbitrum uses the sequencer. This will certainly be updated during development.

# FastAPI
There is an api server that starts up when you run the watcher. There aren't really many endpoints yet but I will be adding them. They will just return JSON.

 - http://127.0.0.1:8000/app/: Gives basic details on the chain and the status.

# Shell Constants
You'll need to add a few things to your `.bashrc/.zshrc` to ensure the connections can be made. I highly recommend using Alchemy if you don't have a local node. If you do, just configure things for that. See the shell-example.txt file for how to add those. The other CREAM tools rely on [Ape](https://github.com/ApeWorX/ape) for a lot of things so you'll see some ape-specific stuff in various files. This project doesn't need Ape, but you'll need to set that stuff up if you use it.

# Work in progress
This is undoubtedly busted in several ways, but I'll be working on it for personal use so it should get refined.