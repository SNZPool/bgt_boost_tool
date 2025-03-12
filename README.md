# BGT Boost Tool

## Overview
The BGT Boost Tool is a web-based application that automates the process of managing BGT token boosts. It provides a simple web interface to monitor BGT statistics and manually control the boost activation process.

## Features
- **Web Interface**: Access the application through a web browser to view BGT statistics and control boost settings.
- **Automated Boost Management**: Automatically queues and activates boosts based on predefined conditions.
- **Logging**: Records all boost-related transactions and activities for auditing purposes.

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
   SECRET_KEY=your_secret_key
   RPC_URL=your_rpc_url
   BGT_CONTRACT_ADDRESS=your_contract_address
   PRIVATE_KEY=your_private_key
   ADDRESS=your_address
   PUBKEY=your_pubkey
   PORT=your_port
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