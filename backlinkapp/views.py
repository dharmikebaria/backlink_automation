# views.py (complete working version)
from django.shortcuts import render, redirect
from django.contrib import messages
import os
from django.conf import settings
import csv
import io
import re
import json
from urllib.parse import urlparse
from datetime import datetime, timedelta
from collections import defaultdict
from .models import Credential
from .utils import parse_result_csv, get_recent_csv_results
from django.http import FileResponse, Http404

def login_view(request):
    """Handle static login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username == 'backlink' and password == 'backlink123':
            request.session['is_logged_in'] = True
            messages.success(request, "Welcome back!")
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    
    # If already logged in, redirect to dashboard
    if request.session.get('is_logged_in'):
        return redirect('dashboard')
        
    return render(request, 'login.html')

def logout_view(request):
    """Handle logout"""
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect('login')

def custom_404_view(request, exception=None, **kwargs):
    """Custom 404 error view"""
    return render(request, '404.html', status=404)

def login_required_custom(view_func):
    """Decorator to restrict access to logged-in users"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_logged_in'):
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required_custom
def dashboard_view(request):
    """Main dashboard view"""
    # Get all credentials for dropdown and manager
    all_credentials = Credential.objects.all()
    active_credentials = [c for c in all_credentials if c.is_active]

    # Get recent results for display
    csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
    
    # Process all results for stats
    all_results = parse_result_csv(csv_path)
    
    # Sort for recent
    recent_results = sorted(all_results, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
    
    # Calculate Today's Success
    today_str = datetime.now().strftime('%Y-%m-%d')
    todays_success = sum(1 for r in all_results if r.get('timestamp', '').startswith(today_str) and r.get('status') == 'success')
    
    # Calculate Success Rate (Total)
    total_runs = len(all_results)
    total_success = sum(1 for r in all_results if r.get('status') == 'success')
    
    # System Status Stats
    last_run = "Never"
    if all_results:
         # Use the most recent one (sorted first)
         last_run_ts = sorted(all_results, key=lambda x: x.get('timestamp', ''), reverse=True)[0].get('timestamp', '')
         try:
             dt = datetime.fromisoformat(last_run_ts)
             last_run = dt.strftime("%Y-%m-%d %H:%M")
         except:
             last_run = last_run_ts

    return render(request, 'dashboard.html', {
        'credentials': active_credentials,
        'all_credentials': all_credentials,
        'recent_results': recent_results,
        'todays_success': todays_success,
        'total_success': total_success,
        'total_runs': total_runs,
        'last_run': last_run,
        'total_credentials_count': all_credentials.count(),
    })

@login_required_custom
def analytics_view(request):
    """Analytics view for detailed stats"""
    csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
    all_results = parse_result_csv(csv_path)
    
    # Initialize aggregators
    daily_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
    weekly_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
    monthly_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
    yearly_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
    
    for r in all_results:
        ts_str = r.get('timestamp', '')
        status = r.get('status', '')
        is_success = status == 'success'
        
        try:
            if not ts_str: continue
            dt = datetime.fromisoformat(ts_str)
            
            # Daily (YYYY-MM-DD)
            daily_stats[dt.strftime('%Y-%m-%d')]['success' if is_success else 'failed'] += 1
            
            # Weekly (YYYY-Www)
            weekly_stats[dt.strftime('%Y-W%U')]['success' if is_success else 'failed'] += 1
            
            # Monthly (YYYY-MM)
            monthly_stats[dt.strftime('%Y-%m')]['success' if is_success else 'failed'] += 1
            
            # Yearly (YYYY)
            yearly_stats[dt.strftime('%Y')]['success' if is_success else 'failed'] += 1
            
        except ValueError:
            continue
    
    def format_data(stats_dict):
        sorted_keys = sorted(stats_dict.keys())
        return {
            'labels': sorted_keys,
            'success': [stats_dict[k]['success'] for k in sorted_keys],
            'failed': [stats_dict[k]['failed'] for k in sorted_keys]
        }
    
    context = {
        'daily_data': json.dumps(format_data(daily_stats)),
        'weekly_data': json.dumps(format_data(weekly_stats)),
        'monthly_data': json.dumps(format_data(monthly_stats)),
        'yearly_data': json.dumps(format_data(yearly_stats)),
    }
    
    return render(request, 'analytics.html', context)

@login_required_custom
def image_manager_view(request):
    img_dir = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'Image')
    os.makedirs(img_dir, exist_ok=True)
    allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    
    def _list_images():
        try:
            files = []
            for name in os.listdir(img_dir):
                p = os.path.join(img_dir, name)
                if os.path.isfile(p) and os.path.splitext(name)[1].lower() in allowed_ext:
                    files.append(name)
            files.sort(key=lambda x: x.lower())
            return files
        except Exception:
            return []
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'upload':
            f = request.FILES.get('image_file')
            if not f:
                messages.error(request, "Please choose an image file")
                return redirect('image_manager')
            name = os.path.basename(f.name)
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed_ext:
                messages.error(request, "Unsupported file type")
                return redirect('image_manager')
            try:
                dst = os.path.join(img_dir, name)
                with open(dst, 'wb+') as out:
                    for chunk in f.chunks():
                        out.write(chunk)
                messages.success(request, f"Image uploaded: {name}")
            except Exception as e:
                messages.error(request, f"Upload failed: {str(e)[:100]}")
            return redirect('image_manager')
        elif action == 'delete':
            name = os.path.basename(request.POST.get('image_name', ''))
            if not name:
                messages.error(request, "Invalid image name")
                return redirect('image_manager')
            try:
                path = os.path.join(img_dir, name)
                if os.path.isfile(path):
                    os.remove(path)
                    messages.success(request, f"Image deleted: {name}")
                else:
                    messages.warning(request, "Image not found")
            except Exception as e:
                messages.error(request, f"Delete failed: {str(e)[:100]}")
            return redirect('image_manager')
        elif action == 'rename':
            old_name = request.POST.get('old_name')
            new_name = request.POST.get('new_name')
            
            if not old_name or not new_name:
                messages.error(request, "Missing filename data")
                return redirect('image_manager')
                
            # Basic validation for new name
            new_name = "".join(x for x in new_name if x.isalnum() or x in "._- ")
            if not new_name:
                 messages.error(request, "Invalid new filename")
                 return redirect('image_manager')

            # Ensure extension is preserved if user didn't type it
            old_ext = os.path.splitext(old_name)[1]
            new_ext = os.path.splitext(new_name)[1]
            if not new_ext:
                new_name += old_ext
            elif new_ext.lower() != old_ext.lower():
                # Prevent changing extension to something potentially dangerous or just different
                messages.error(request, "Changing file extension is not allowed")
                return redirect('image_manager')

            old_path = os.path.join(img_dir, old_name)
            new_path = os.path.join(img_dir, new_name)

            if not os.path.exists(old_path):
                messages.error(request, "Original file not found")
            elif os.path.exists(new_path):
                messages.error(request, "A file with that name already exists")
            else:
                try:
                    os.rename(old_path, new_path)
                    messages.success(request, f"Renamed to {new_name}")
                except Exception as e:
                    messages.error(request, f"Rename failed: {str(e)}")
            return redirect('image_manager')
    
    images = _list_images()
    return render(request, 'image.html', {'images': images})

@login_required_custom
def serve_image_view(request, filename: str):
    img_dir = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'Image')
    safe_name = os.path.basename(filename)
    path = os.path.join(img_dir, safe_name)
    if not os.path.isfile(path):
        raise Http404("Image not found")
    try:
        import mimetypes
        mime, _ = mimetypes.guess_type(path)
        return FileResponse(open(path, 'rb'), content_type=mime or 'application/octet-stream')
    except Exception:
        raise Http404("Unable to serve image")

def load_excel_view(request):
    """Load credentials from Excel file"""
    try:
        success, message = Credential.load_from_excel()
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return redirect('dashboard')

def upload_excel_view(request):
    """Handle Excel file upload"""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        # Save to your location
        upload_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'credentials.xlsx')
        
        try:
            # Save the uploaded file
            with open(upload_path, 'wb+') as destination:
                for chunk in excel_file.chunks():
                    destination.write(chunk)
            
            messages.success(request, f"✅ Excel file uploaded successfully")
            
            # Auto-load after upload
            success, load_message = Credential.load_from_excel()
            if success:
                messages.success(request, load_message)
            else:
                messages.warning(request, f"Uploaded but loading failed: {load_message}")
                
        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")
    
    return redirect('dashboard')

def upload_csv_view(request):
    """Import credentials from a CSV or Excel uploaded via modal"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        uploaded_file = request.FILES['csv_file']
        file_name = uploaded_file.name.lower()
        
        # Check if it's actually an Excel file
        if file_name.endswith(('.xlsx', '.xls')):
            try:
                # Save temp file
                temp_path = os.path.join(settings.BASE_DIR, 'temp_upload.xlsx')
                with open(temp_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Use existing Excel loader
                success, message = Credential.load_from_excel(temp_path)
                
                # Cleanup
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
                    
            except Exception as e:
                messages.error(request, f"Excel import failed: {str(e)}")
            return redirect('dashboard')

        try:
            # Read CSV content with universal newlines support
            # Use newline=None to handle \r\n, \r, or \n automatically
            data = csv_file.read().decode('utf-8', errors='replace')
            
            # Pre-process data to ensure clean lines if needed, or rely on io.StringIO
            # Using newline=None in StringIO is not directly supported, but splitlines works
            # Better approach: split by lines and rejoin, or just trust StringIO with clean input
            # The specific error "new-line character seen in unquoted field" usually means
            # the CSV parser is confused by mixed line endings within a field or unquoted fields with newlines.
            
            # Robust fix: Use io.StringIO on the decoded string.
            # Python's CSV module handles this better if we don't manually mess with it,
            # BUT for uploaded files, decoding + StringIO is standard.
            # The error suggests the input might have bare \r or \n inside fields without quotes.
            
            stream = io.StringIO(data, newline=None)
            reader = csv.DictReader(stream)
            
            # Helper to find key case-insensitively
            def get_val(row, keys):
                row_keys_lower = {k.lower().strip(): k for k in row.keys() if k}
                for k in keys:
                    if k.lower() in row_keys_lower:
                        return row[row_keys_lower[k.lower()]]
                return None

            created = 0
            updated = 0
            skipped = 0
            
            for row in reader:
                # Flexible header matching
                url = (get_val(row, ['url', 'website', 'link', 'site', 'address']) or '').strip()
                email = (get_val(row, ['email', 'mail', 'login', 'e-mail']) or '').strip() or None
                username = (get_val(row, ['username', 'user', 'id', 'login']) or '').strip() or None
                password = (get_val(row, ['password', 'pass', 'pwd', 'secret']) or '').strip()
                
                # Active status
                is_active_val = (get_val(row, ['is_active', 'active', 'enabled']) or '').strip().lower()
                is_active = True if is_active_val in ['', '1', 'true', 'yes', 'y'] else False
                
                if not url or not password:
                    print(f"Skipped row: {row} (URL or Password missing)")
                    skipped += 1
                    continue

                # Upsert by URL
                obj, exists = None, False
                try:
                    obj = Credential.objects.get(url=url)
                    exists = True
                except Credential.DoesNotExist:
                    obj = Credential(url=url)
                
                if email: obj.email = email
                if username: obj.username = username
                obj.password = password
                obj.is_active = is_active
                obj.save()
                
                if exists:
                    updated += 1
                else:
                    created += 1
            
            messages.success(request, f"Imported CSV: {created} created, {updated} updated, {skipped} skipped")
        except Exception as e:
            messages.error(request, f"CSV import failed: {str(e)[:150]}")
    else:
        messages.error(request, "No CSV file provided")
    return redirect('dashboard')

from django.http import HttpResponseRedirect
import subprocess
import sys

@login_required_custom
def add_credential_view(request):
    """Add a single credential manually"""
    if request.method == 'POST':
        website = request.POST.get('website')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not website or not password:
            messages.error(request, "Website and Password are required")
            return redirect('dashboard')
            
        try:
            # Check if exists
            if Credential.objects.filter(url=website, username=username).exists():
                messages.warning(request, "This credential already exists")
                return redirect('dashboard')
                
            Credential.objects.create(
                url=website,
                email=email,
                username=username,
                password=password,
                is_active=True
            )
            messages.success(request, f"✅ Credential for {website} added successfully")
        except Exception as e:
            messages.error(request, f"Error adding credential: {str(e)}")
            
    return redirect('dashboard')

@login_required_custom
def run_automation_view(request):
    """Run automation for selected credential - FIXED VERSION"""
    print("\n" + "="*60)
    print("🔍 DEBUG: run_automation_view STARTED")
    print(f"DEBUG: Request method: {request.method}")
    
    if request.method == 'POST':
        credential_id = request.POST.get('credential_id')
        print(f"DEBUG: Credential ID from form: {credential_id}")
        
        if not credential_id:
            messages.error(request, "❌ Please select a credential")
            return redirect('dashboard')
        
        try:
            import time
            # Check if "Run All" selected
            if credential_id == '__all__':
                print("DEBUG: Running ALL active credentials")
                credentials = Credential.objects.filter(is_active=True)
                if not credentials.exists():
                    messages.warning(request, "No active credentials found to run.")
                    return redirect('dashboard')
                
                creds_list = []
                for c in credentials:
                    creds_list.append({
                        'website': c.url,
                        'email': c.email or '',
                        'username': c.username or '',
                        'password': c.password
                    })
                
                # Use a temp file for batch
                script_dir = os.path.dirname(os.path.join(settings.BASE_DIR, 'Advance Backlink', 'script.py'))
                temp_json_path = os.path.join(script_dir, f'batch_run_{int(time.time())}.json')
                
                with open(temp_json_path, 'w', encoding='utf-8') as f:
                    json.dump(creds_list, f, indent=2)
                    
                credential_info = "All Active Websites"
                
            else:
                # Get credential from database
                credential = Credential.objects.get(id=credential_id)
                print(f"DEBUG: Found credential - URL: {credential.url}")
                print(f"DEBUG: Email: {credential.email}, Username: {credential.username}")
                
                credential_info = credential.url
                
                single_cred = [{
                    'website': credential.url,
                    'email': credential.email or '',
                    'username': credential.username or '',
                    'password': credential.password
                }]
                
                script_dir = os.path.dirname(os.path.join(settings.BASE_DIR, 'Advance Backlink', 'script.py'))
                temp_json_path = os.path.join(script_dir, f'single_run_{credential.id}.json')
                
                with open(temp_json_path, 'w', encoding='utf-8') as f:
                    json.dump(single_cred, f, indent=2)

            # Paths
            script_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'script.py')
            csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
            
            # Verify script exists
            if not os.path.exists(script_path):
                print(f"❌ ERROR: Script not found at {script_path}")
                messages.error(request, f"❌ Script file not found")
                return redirect('dashboard')
            
            # Prepare command to run script
            cmd = [
                sys.executable,  # Use same Python interpreter
                script_path,
                '--creds-json', temp_json_path
            ]
            
            print(f"DEBUG: Running command: {' '.join(cmd)}")
            
            # Run the script
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',  # Explicitly use UTF-8 to handle emojis
                    errors='replace',  # Don't crash on encoding errors
                    timeout=600,  # 10 minute timeout for batch
                    cwd=script_dir,  # Run from script's directory
                    shell=False
                )
                
                # Clean up temp file
                try:
                    if os.path.exists(temp_json_path):
                        os.remove(temp_json_path)
                except:
                    pass
                
                print(f"DEBUG: Script return code: {result.returncode}")
                print(f"DEBUG: Script stdout (first 200 chars): {result.stdout[:200]}")
                print(f"DEBUG: Script stderr: {result.stderr[:200] if result.stderr else 'None'}")
                
                if result.returncode == 0:
                    # ✅ SCRIPT SUCCESS
                    print("✅ DEBUG: Script executed successfully!")
                    
                    # Store success in session
                    request.session['last_run'] = {
                        'status': 'success',
                        'credential_url': credential_info,
                        'credential_email': 'Multiple' if credential_id == '__all__' else '',
                        'credential_username': 'Multiple' if credential_id == '__all__' else '',
                        'output': result.stdout[:500],
                        'timestamp': 'Now'
                    }
                    
                    messages.success(request, f"✅ Automation completed successfully for {credential_info}!")
                else:
                    # ❌ SCRIPT FAILURE
                    print("❌ DEBUG: Script failed!")
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    messages.error(request, f"❌ Automation failed for {credential_info}: {error_msg[:200]}")
                    
            except subprocess.TimeoutExpired:
                print("❌ DEBUG: Script timed out")
                messages.error(request, f"❌ Automation timed out for {credential_info}")
            except Exception as e:
                print(f"❌ DEBUG: Subprocess error: {e}")
                messages.error(request, f"❌ Error running script: {str(e)}")

        except Credential.DoesNotExist:
            messages.error(request, "Credential not found")
        except Exception as e:
            print(f"❌ DEBUG: General error: {e}")
            messages.error(request, f"Error: {str(e)}")
            
        return redirect('dashboard')
    
    print("DEBUG: Not a POST request")
    return redirect('dashboard')

def success_page_view(request):
    """Simple success page for testing"""
    last_run = request.session.get('last_run', {})
    
    print(f"DEBUG: Success page accessed. Session data: {last_run}")
    
    if not last_run:
        print("⚠️ DEBUG: No session data found, redirecting to dashboard")
        messages.warning(request, "No recent automation run found")
        return redirect('dashboard')
    
    # Clear session after showing (optional)
    # if 'last_run' in request.session:
    #     del request.session['last_run']
    
    return render(request, 'success.html', {
        'run_data': last_run
    })

from django.views.decorators.http import require_POST
from math import ceil
from datetime import datetime, date, timedelta
from .utils import parse_result_csv

import json

@login_required_custom
def blog_update_view(request):
    blog_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'blog.txt')
    
    if request.method == 'POST':
        try:
            content = request.POST.get('content', '')
            print(f"DEBUG: Raw content received (len={len(content)}): {repr(content[:100])}...")
            
            # Treat content as plain text; just normalize newlines
            if content:
                content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            print(f"DEBUG: Plain content to save (len={len(content)}): {repr(content[:100])}...")
            
            # Save to file
            try:
                with open(blog_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content or '')
                
                # Verify write
                if os.path.exists(blog_path):
                    file_size = os.path.getsize(blog_path)
                    print(f"DEBUG: Successfully wrote to {blog_path}. Size: {file_size} bytes")
                else:
                    print(f"ERROR: File {blog_path} does not exist after write!")
                    
                messages.success(request, "✅ Blog content updated successfully!")
            except Exception as e:
                print(f"ERROR: Failed to write to file: {e}")
                messages.error(request, f"Error saving file: {str(e)}")

            # Update session selected websites
            selected_ids = request.POST.getlist('selected_websites')
            request.session['selected_websites'] = selected_ids
            request.session.modified = True
            
            # NOTE: Automation script execution removed from save flow to prevent timeouts.
            # Use the "Run" feature separately if needed.
            
        except Exception as e:
            print(f"ERROR: Failed to save blog (outer): {e}")
            messages.error(request, f"Error saving blog: {str(e)[:100]}")
                
        # Cache-busting redirect
        from django.urls import reverse
        return redirect(f"{reverse('blog_update')}?t={int(datetime.now().timestamp())}")

    # GET request
    content = ''
    try:
        if os.path.exists(blog_path):
            with open(blog_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            default_content = "Title\n\nContent..."
            with open(blog_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(default_content)
            content = default_content
    except Exception as e:
        print(f"ERROR: Failed to read blog: {e}")
        content = ''
        
    # Get credentials for dropdown
    credentials = Credential.objects.filter(is_active=True)
    
    # Get previously selected websites from session
    selected_websites = request.session.get('selected_websites')
    
    if selected_websites is None:
        selected_websites = [str(c.id) for c in credentials]
    else:
        selected_websites = [str(x) for x in selected_websites]
        
    response = render(request, 'blog_update.html', {
        'blog_path': blog_path,
        'blog_content': content,
        'credentials': credentials,
        'selected_websites': selected_websites
    })
    try:
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
    except Exception:
        pass
    return response

@require_POST
@login_required_custom
def add_credential_view(request):
    try:
        url = request.POST.get('url', '').strip()
        email = request.POST.get('email', '').strip() or None
        username = request.POST.get('username', '').strip() or None
        password = request.POST.get('password', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        if not url or not password:
            messages.error(request, "URL and password are required")
            return redirect('dashboard')
        obj = Credential.objects.create(
            url=url, email=email, username=username, password=password, is_active=is_active
        )
        messages.success(request, "Credential added")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"Error adding credential: {str(e)[:100]}")
        return redirect('dashboard')

@require_POST
@login_required_custom
def edit_credential_view(request):
    try:
        cred_id = request.POST.get('id')
        cred = Credential.objects.get(id=cred_id)
        url = request.POST.get('url', '').strip() or cred.url
        email = request.POST.get('email', '').strip() or None
        username = request.POST.get('username', '').strip() or None
        password = request.POST.get('password', '').strip() or cred.password
        is_active = request.POST.get('is_active') == 'on'
        cred.url = url
        cred.email = email
        cred.username = username
        cred.password = password
        cred.is_active = is_active
        cred.save()
        messages.success(request, "Credential updated")
        return redirect('dashboard')
    except Credential.DoesNotExist:
        messages.error(request, "Credential not found")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"Error updating credential: {str(e)[:100]}")
        return redirect('dashboard')

@require_POST
@login_required_custom
def delete_credential_view(request):
    try:
        cred_id = request.POST.get('id')
        cred = Credential.objects.get(id=cred_id)
        cred.delete()
        messages.success(request, "Credential deleted")
        return redirect('dashboard')
    except Credential.DoesNotExist:
        messages.error(request, "Credential not found")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"Error deleting credential: {str(e)[:100]}")
        return redirect('dashboard')

@require_POST
def publish_blog_view(request):
    return redirect('blog_update')

@login_required_custom
def history_view(request):
    csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
    status = request.GET.get('status', 'all').lower()
    page = int(request.GET.get('page', '1') or '1')
    page_size = int(request.GET.get('page_size', '20') or '20')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    preset = request.GET.get('preset', '')

    # Compute date range presets
    today = date.today()
    if preset == 'today':
        start_date = today
        end_date = today
    elif preset == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif preset == 'month':
        start_date = today.replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    else:
        start_date = None
        end_date = None

    # Override with explicit dates if provided
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str).date()
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str).date()
    except Exception:
        pass

    # Load and sort
    records = parse_result_csv(csv_path)
    def parse_ts(ts):
        try:
            return datetime.fromisoformat(ts.replace('Z',''))
        except Exception:
            return datetime.min
    records = [r for r in records if not r.get('error')]
    for r in records:
        r['id'] = f"{r.get('timestamp','')}|{r.get('website','')}"
    records.sort(key=lambda x: parse_ts(x.get('timestamp','')), reverse=True)

    # Status filter
    if status in ('success', 'failed'):
        records = [r for r in records if (r.get('status','').lower() == status)]

    # Date filter
    if start_date or end_date:
        def in_range(r):
            d = parse_ts(r.get('timestamp','')).date()
            if start_date and d < start_date:
                return False
            if end_date and d > end_date:
                return False
            return True
        records = [r for r in records if in_range(r)]

    # Calculate Website Stats (Based on Active Credentials)
    # Get active credentials first
    active_credentials = Credential.objects.filter(is_active=True)
    
    def get_domain(url):
        if not url: return 'Unknown'
        # Handle simple names
        if not url.startswith(('http://', 'https://')): return url
        try:
            netloc = urlparse(url).netloc
            if netloc.startswith('www.'): netloc = netloc[4:]
            return netloc
        except:
            return url
            
    # Pre-calculate domain for each credential for matching
    cred_map = []
    for cred in active_credentials:
        cred_map.append({
            'obj': cred,
            'domain': get_domain(cred.url),
            'display_name': f"{cred.url} - {cred.username}" if cred.username else cred.url
        })
    
    website_stats_list = []
    
    for item in cred_map:
        # Filter records that match this credential's domain
        # Note: This might aggregate history for multiple credentials if they share the same domain
        # but since we can't distinguish better from CSV, this is the best approximation.
        matched_records = [r for r in records if get_domain(r.get('website', '')) == item['domain']]
        
        total = len(matched_records)
        success = sum(1 for r in matched_records if r.get('status', '').lower() == 'success')
        failed = sum(1 for r in matched_records if r.get('status', '').lower() == 'failed')
        
        website_stats_list.append({
            'label': item['domain'],
            'domain_filter': item['domain'], # Use domain for filtering
            'total': total,
            'success': success,
            'failed': failed
        })

    # Sort by total count descending
    # website_stats_list.sort(key=lambda x: x['total'], reverse=True) # User might want fixed order? Let's stick to total for now or keep db order? 
    # User said "only 7 block like how many total website is there". 
    # Usually consistent order is better. Let's keep DB order or alphabetical?
    # Let's keep DB order (creation order usually). Or maybe sort by website name?
    # Let's sort by website name for stability.
    website_stats_list.sort(key=lambda x: x['label'])

    # Platform Filter
    platform_filter = request.GET.get('platform', '')
    if platform_filter:
        records = [r for r in records if get_domain(r.get('website', '')) == platform_filter]

    total_count = len(records)
    page_size = int(request.GET.get('page_size', '20') or '20') # Re-read page_size just in case, though it's already read at top.
    # Actually page_size is read at the top of function.
    
    total_pages = ceil(total_count / page_size) if page_size > 0 else 1
    page = max(1, min(page, total_pages if total_pages else 1))
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = records[start_idx:end_idx]

    success_count = sum(1 for r in records if r.get('status','').lower() == 'success')
    failed_count = sum(1 for r in records if r.get('status','').lower() == 'failed')

    return render(request, 'history.html', {
        'records': page_records,
        'page': page,
        'page_size': page_size,
        'page_sizes': [10, 20, 50, 100],
        'total_count': total_count,
        'total_pages': total_pages,
        'status': status,
        'success_count': success_count,
        'failed_count': failed_count,
        'website_stats': website_stats_list,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'preset': preset,
        'csv_path': csv_path,
        'platform_filter': platform_filter
    })

@require_POST
def history_delete_view(request):
    csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
    record_id = request.POST.get('id', '')
    try:
        # Read all rows
        import csv
        rows = []
        header = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0 and 'timestamp' in row:
                    header = row
                    continue
                rows.append(row)
        # Filter out matching row
        keep = []
        for row in rows:
            if len(row) < 2:
                keep.append(row)
                continue
            rid = f"{row[0]}|{row[1]}"
            if rid == record_id:
                continue
            keep.append(row)
        # Write back
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
            for row in keep:
                writer.writerow(row)
        messages.success(request, "Record deleted")
    except Exception as e:
        messages.error(request, f"Delete failed: {str(e)[:100]}")
    return redirect('history')

@require_POST
def history_bulk_delete_view(request):
    csv_path = os.path.join(settings.BASE_DIR, 'Advance Backlink', 'results.csv')
    ids = request.POST.getlist('ids')
    try:
        import csv
        rows = []
        header = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0 and 'timestamp' in row:
                    header = row
                    continue
                rows.append(row)
        id_set = set(ids)
        keep = []
        for row in rows:
            if len(row) < 2:
                keep.append(row)
                continue
            rid = f"{row[0]}|{row[1]}"
            if rid in id_set:
                continue
            keep.append(row)
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
            for row in keep:
                writer.writerow(row)
        messages.success(request, f"Deleted {len(ids)} record(s)")
    except Exception as e:
        messages.error(request, f"Bulk delete failed: {str(e)[:100]}")
    return redirect('history')
