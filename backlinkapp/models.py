# models.py (with better error handling)
from django.db import models
import pandas as pd
import os
from django.conf import settings

class Credential(models.Model):
    url = models.URLField(max_length=500)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(max_length=500)
    username = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.url} ({self.username or self.email})"
    
    @classmethod
    def load_from_excel(cls, excel_path=None):
        """
        Loads credentials from your specific Excel format:
        Columns: url, email_selector, password_selector, username_selector
        """
        # Use your exact path if not provided
        if not excel_path:
            excel_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'credentials.xlsx')
        
        # Convert to absolute path
        excel_path = os.path.abspath(excel_path)
        
        print(f"🔍 Looking for Excel at: {excel_path}")
        print(f"🔍 File exists: {os.path.exists(excel_path)}")
        
        if not os.path.exists(excel_path):
            # Try to find it
            print("⚠️ File not found, searching in parent directories...")
            for root, dirs, files in os.walk(str(settings.BASE_DIR)):
                if 'credentials.xlsx' in files:
                    excel_path = os.path.join(root, 'credentials.xlsx')
                    print(f"✅ Found Excel at: {excel_path}")
                    break
        
        if not os.path.exists(excel_path):
            error_msg = f"❌ Excel file not found at: {excel_path}"
            print(error_msg)
            return False, error_msg
        
        try:
            # Read Excel file
            print(f"📖 Reading Excel: {excel_path}")
            df = pd.read_excel(excel_path)
            print(f"✅ Successfully read Excel")
            print(f"📊 Columns found: {list(df.columns)}")
            print(f"📋 Total rows: {len(df)}")
            
            if len(df) == 0:
                return False, "Excel file is empty"
            
            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]
            print(f"🔧 Cleaned columns: {list(df.columns)}")
            
            # Check for required columns
            required_columns = ['url']
            for col in required_columns:
                if col not in df.columns:
                    return False, f"Required column '{col}' not found in Excel"
            
            # Process each row
            records_processed = 0
            records_created = 0
            records_updated = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('url')) or str(row.get('url', '')).strip() == '':
                        continue
                    
                    # Extract values
                    url = str(row.get('url', '')).strip()
                    
                    # Handle different column names
                    email = ''
                    if 'email_selector' in df.columns:
                        email_val = row.get('email_selector')
                        email = str(email_val).strip() if pd.notna(email_val) else ''
                    elif 'email' in df.columns:
                        email_val = row.get('email')
                        email = str(email_val).strip() if pd.notna(email_val) else ''
                    
                    password = ''
                    if 'password_selector' in df.columns:
                        pass_val = row.get('password_selector')
                        password = str(pass_val).strip() if pd.notna(pass_val) else ''
                    elif 'password' in df.columns:
                        pass_val = row.get('password')
                        password = str(pass_val).strip() if pd.notna(pass_val) else ''
                    
                    username = ''
                    if 'username_selector' in df.columns:
                        user_val = row.get('username_selector')
                        username = str(user_val).strip() if pd.notna(user_val) else ''
                    elif 'username' in df.columns:
                        user_val = row.get('username')
                        username = str(user_val).strip() if pd.notna(user_val) else ''
                    
                    # Debug
                    print(f"Row {index}: URL={url}, Email={email}, User={username}, PassLen={len(password)}")
                    
                    # Create or update
                    obj, created = cls.objects.update_or_create(
                        url=url,
                        defaults={
                            'email': email if email else None,
                            'password': password,
                            'username': username if username else None,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        records_created += 1
                    else:
                        records_updated += 1
                    
                    records_processed += 1
                    
                except Exception as e:
                    errors.append(f"Row {index} error: {str(e)}")
                    print(f"❌ Error in row {index}: {e}")
                    continue
            
            # Result message
            msg = f"✅ Processed {records_processed} records ({records_created} created, {records_updated} updated)"
            if errors:
                msg += f". {len(errors)} errors occurred."
            
            return True, msg
            
        except Exception as e:
            import traceback
            print(f"❌ Error reading Excel: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False, f"Error reading Excel: {str(e)}"