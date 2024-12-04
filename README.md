# Distributed Nodes

Simulation of nodes in a distributed system. The nodes communicate with each other using TCP sockets.
This project aims to analyze key reliability and performance metrics such as MTTR (Mean Time To Repair), MTTB (Mean Time To Breakdown), and availability.

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
