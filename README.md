# Simple POS System

A simple Point of Sale (POS) system built with Flask and SQLite.

## Features

- User authentication
- Product management
- Sales processing
- Inventory tracking
- Sales history

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the application at `http://localhost:5000`

## Default Admin Account

On first run, you'll need to create a user account. You can modify the `app.py` file to create an admin account.

## Usage

1. Login with your credentials
2. Use the dashboard to navigate to different sections:
   - POS: Process sales
   - Products: Manage inventory
   - Sales: View sales history

## Security Notes

- Change the `SECRET_KEY` in `app.py` before deploying
- Implement proper user management
- Add additional security measures for production use 