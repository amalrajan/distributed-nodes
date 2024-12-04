# Distributed Nodes

Simulation of nodes in a distributed system. The nodes communicate with each other using TCP sockets.

## Overview

This project aims to analyze key reliability and performance metrics such as MTTR (Mean Time To Repair), MTTB (Mean Time To Breakdown), and availability.

The system consists of a supervisor node and multiple worker nodes. The supervisor node is responsible for monitoring the worker nodes. The worker nodes are responsible for executing the tasks.

The supervisor sends a SIGUSR1 signal to the worker nodes to instruct clients to connect to the server. The supervisor keeps polling the PID of the worker nodes to check if they are alive. If a worker node is not responding, the supervisor restarts the worker node.

## Installation

```bash
git clone https://github.com/amalrajan/distributed-nodes
cd distributed-nodes
pip install -r requirements.txt
```

## Usage

```bash
python supervisor.py
```

## Availability Analysis

```bash
python tests/test_mttr_mttb.py
```

## License

[MIT License](https://choosealicense.com/licenses/mit/)
