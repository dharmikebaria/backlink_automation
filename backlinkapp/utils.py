# utils.py (create this file in your Django app folder)
import subprocess
import os
import csv
import json
from django.conf import settings

def run_automation_script(script_path, args_dict):
    """
    Runs your automation script with the provided arguments.
    Updated to work with your existing script.py
    """
    try:
        # Debug: Print what we're about to runcle
        print(f"🔧 Running script: {script_path}")
        print(f"🔧 Arguments: {args_dict}")
        
        # Method 1: Create a temporary credentials file for your script
        # Since your script reads from credentials.xlsx, we'll update that file
        # with just the selected credential
        
        # First backup the original Excel if it exists
        excel_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'credentials.xlsx')
        backup_path = excel_path + '.backup'
        
        import pandas as pd
        import shutil
        
        # Create a single-row DataFrame with the selected credential
        df_single = pd.DataFrame([{
            'url': args_dict.get('url', ''),
            'email_selector': args_dict.get('email', ''),
            'password_selector': args_dict.get('password', ''),
            'username_selector': args_dict.get('username', '')
        }])
        
        # Backup original if exists
        if os.path.exists(excel_path):
            shutil.copy2(excel_path, backup_path)
        
        # Write single credential to Excel
        df_single.to_excel(excel_path, index=False)
        print(f"✅ Created temporary Excel with single credential: {args_dict.get('url')}")
        
        # Method 2: Run your script directly
        # Your script.py should be modified to accept command line arguments
        # If not, we'll run it as-is since it now reads the single credential
        
        cmd = ['python', script_path]
        
        # Execute the script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(script_path),  # Run from script's directory
            shell=True  # For Windows compatibility
        )
        
        print(f"📊 Script return code: {result.returncode}")
        print(f"📊 Script stdout length: {len(result.stdout)} chars")
        print(f"📊 Script stderr length: {len(result.stderr)} chars")
        
        # Restore original Excel if we backed it up
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, excel_path)
            os.remove(backup_path)
            print("✅ Restored original Excel file")
        
        if result.returncode == 0:
            # Try to parse output
            output = result.stdout.strip()
            if not output:
                output = "Script executed successfully (no output)"
            
            return True, output
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return False, f"Script error: {error_msg[:200]}"
    
    except subprocess.TimeoutExpired:
        # Restore backup if timeout
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, excel_path)
            os.remove(backup_path)
        return False, "Script execution timed out after 5 minutes."
    except FileNotFoundError:
        return False, f"Script file not found: {script_path}"
    except Exception as e:
        import traceback
        print(f"❌ Execution error details: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False, f"Execution error: {str(e)}"

def parse_result_csv(csv_path):
    """
    Parses the result.csv file to get detailed logs.
    Returns a list of dictionaries for template display.
    """
    results = []
    try:
        if not os.path.exists(csv_path):
            return [{'error': f'CSV file not found at: {csv_path}'}]
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Try different CSV formats
            content = f.read()
            lines = content.strip().split('\n')
            
            if len(lines) > 0:
                # Check if it has headers
                first_line = lines[0]
                if ',' in first_line and 'timestamp' in first_line.lower():
                    # Has headers
                    f.seek(0)
                    reader = csv.DictReader(f)
                    for row in reader:
                        results.append({
                            'timestamp': row.get('timestamp', ''),
                            'website': row.get('website', ''),
                            'status': row.get('status', ''),
                            'message': row.get('message', ''),
                            'profile_reached': row.get('profile_reached', ''),
                            'final_url': row.get('final_url', ''),
                            'screenshot': row.get('screenshot', '')
                        })
                else:
                    # No headers - parse based on your format
                    for line in lines:
                        parts = line.split(',')
                        if len(parts) >= 6:
                            results.append({
                                'timestamp': parts[0],
                                'website': parts[1],
                                'status': parts[2],
                                'message': parts[3],
                                'profile_reached': parts[4],
                                'final_url': parts[5] if len(parts) > 5 else '',
                                'screenshot': parts[6] if len(parts) > 6 else ''
                            })
        
        print(f"✅ Parsed {len(results)} records from CSV")
        return results
    
    except Exception as e:
        print(f"❌ CSV parsing error: {str(e)}")
        return [{'error': f'Error parsing CSV: {str(e)}'}]

def get_recent_csv_results(csv_path, limit=10):
    """
    Gets the most recent results from CSV for dashboard display
    """
    results = parse_result_csv(csv_path)
    # Sort by timestamp descending
    try:
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    except:
        pass
    return results[:limit]
