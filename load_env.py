#!/usr/bin/env python3
"""
Script to load environment variables from .env file for local testing
"""

import os
import sys
from pathlib import Path

def load_env_file(env_file_path='.env'):
    """Load environment variables from .env file"""
    env_path = Path(env_file_path)
    
    if not env_path.exists():
        print(f"❌ Environment file {env_file_path} not found!")
        print(f"📝 Please copy env.example to {env_file_path} and fill in your values")
        return False
    
    print(f"📁 Loading environment variables from {env_file_path}")
    
    with open(env_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                os.environ[key] = value
                print(f"  ✅ Loaded: {key}")
            else:
                print(f"  ⚠️  Skipping invalid line {line_num}: {line}")
    
    print(f"✅ Environment variables loaded successfully!")
    return True

def check_required_vars():
    """Check if required environment variables are set"""
    required_vars = ['GOOGLE_SERVICE_ACCOUNT', 'GOOGLE_SHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("📝 Please check your .env file and ensure all required variables are set")
        return False
    
    print("✅ All required environment variables are set!")
    return True

def main():
    """Main function to load environment and run tests"""
    print("🌊 Setting up local environment for Red Tide Florida testing...")
    
    # Load environment variables
    if not load_env_file():
        sys.exit(1)
    
    # Check required variables
    if not check_required_vars():
        sys.exit(1)
    
    print("\n🚀 Environment is ready! You can now run:")
    print("   python fetch_hab_data.py")
    print("   python sync_to_wordpress.py")
    print("   python verify_sheet_headers.py")

if __name__ == "__main__":
    main()
