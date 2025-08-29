#!/bin/bash

# Setup script for local environment testing

echo "🌊 Setting up local environment for Red Tide Florida testing..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your actual values:"
    echo "   - GOOGLE_SERVICE_ACCOUNT: Your Google service account JSON"
    echo "   - GOOGLE_SHEET_ID: Your Google Sheets ID"
    echo ""
    echo "📖 Instructions:"
    echo "   1. Get your Google service account credentials from Google Cloud Console"
    echo "   2. Copy the JSON content to GOOGLE_SERVICE_ACCOUNT in .env"
    echo "   3. Get your Google Sheets ID from the URL of your sheet"
    echo "   4. Update GOOGLE_SHEET_ID in .env"
    echo ""
    echo "🔗 Helpful links:"
    echo "   - Google Cloud Console: https://console.cloud.google.com/"
    echo "   - Google Sheets API: https://developers.google.com/sheets/api"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🚀 Setup complete! You can now run:"
echo "   source venv/bin/activate"
echo "   python test_fwc_only.py          # Test FWC API without Google Sheets"
echo "   python load_env.py               # Load environment and check setup"
echo "   python fetch_hab_data.py         # Run full HAB data fetch (requires .env)"
echo ""
echo "💡 For testing without Google Sheets, use:"
echo "   python test_fwc_only.py"
