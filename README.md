# BGT Boost Tool

## Overview
The BGT Boost Tool is a application that automates the process of managing BGT token boosts. It provides a simple web interface to monitor BGT statistics.

## Features
- **Web Interface**: Access the application through a web browser to view BGT statistics.
- **Automated Boost Management**: Automatically queues and activates boosts based on predefined conditions.
- **Logging**: Records all boost-related transactions and activities for auditing purposes.
- **Persistent Storage**: Stores all task information in a SQLite database located in the `data` directory.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the root directory and set the following variables:
   ```
   RPC_URL=your_rpc_url
   DEPOSIT_CONTRACT_ADDRESS=0x4242424242424242424242424242424242424242
   BGT_CONTRACT_ADDRESS=0x656b95E550C07a9ffe548bd4085c72418Ceb1dba
   REWARD_CONTRACT_ADDRESS=0x44F07Ce5AfeCbCC406e6beFD40cc2998eEb8c7C6
   PRIVATE_KEY=your_private_key
   ADDRESS=your_address
   PUBKEY=your_pubkey
   PORT=your_port
   INTERVAL=periodic_interval
   MODE=OBSERVATION
   ```

4. **Run the application**:
   ```bash
   python run.py
   ```

## Usage
- Access the web interface at `http://localhost:<PORT>`.
- Use the interface to view BGT statistics and toggle the boost feature.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details. 