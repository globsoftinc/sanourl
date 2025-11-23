from flask import Flask, render_template, request, jsonify, redirect, make_response
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
import string
import random
import re
import requests

load_dotenv()

# Environment variables
turnstile_secret = os.getenv("TURNSTILE_SECRET_KEY")
turnstile_site_key = os.getenv("TURNSTILE_SITE_KEY")
mongo_uri = os.getenv("MONGO_URI")

# MongoDB client
client = MongoClient(mongo_uri)

# Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Database and collections
db = client["sanourl_db"]
urls_collection = db["urls"]

# Newsletter database and collection
emails_db = client["emails_db"]
emails_collection = emails_db["emails"]


def get_client_ip():
    """Get real client IP (works with Cloudflare)"""
    # Cloudflare sends real IP in CF-Connecting-IP header
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip
    
    # Fallback to X-Forwarded-For
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    
    # Final fallback
    return request.remote_addr


def verify_turnstile(token):
    """Verify Cloudflare Turnstile token"""
    if not token:
        app.logger.error("No Turnstile token provided")
        return False
    
    if not turnstile_secret:
        app.logger.error("TURNSTILE_SECRET_KEY not set in environment")
        return False
    
    try:
        client_ip = get_client_ip()
        
        app.logger.info(f"Verifying Turnstile token from IP: {client_ip}")
        
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': turnstile_secret,
                'response': token,
                'remoteip': client_ip  # THIS WAS MISSING!
            },
            timeout=10
        )
        
        result = response.json()
        
        app.logger.info(f"Turnstile verification result: {result}")
        
        if not result.get('success', False):
            app.logger.error(f"Turnstile verification failed: {result.get('error-codes', [])}")
        
        return result.get('success', False)
    
    except requests.exceptions.Timeout:
        app.logger.error("Turnstile verification timeout")
        return False
    except Exception as e:
        app.logger.error(f"Turnstile verification error: {str(e)}")
        return False


def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_url(url):
    """Validate URL format"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$|^[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


def generate_short_code(length=6):
    """Generate a random short code for URLs"""
    characters = string.ascii_letters + string.digits
    while True:
        short_code = ''.join(random.choice(characters) for _ in range(length))
        if not urls_collection.find_one({"short_code": short_code}):
            return short_code


@app.route("/", methods=['GET'])
def index():
    """Landing page for SanoURL"""
    return render_template('index.html', turnstile_site_key=turnstile_site_key)


@app.route("/subscribe", methods=['POST'])
def subscribe():
    """Subscribe email to newsletter"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        turnstile_token = data.get("turnstile_token", "")
        
        # Verify Turnstile
        if not verify_turnstile(turnstile_token):
            return jsonify({"success": False, "error": "Verification failed. Please try again."}), 400

        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400
        
        if not is_valid_email(email):
            return jsonify({"success": False, "error": "Invalid email format"}), 400
        
        # Check if email already exists
        existing_email = emails_collection.find_one({"email": email, "source": "SanoURL"})
        
        if existing_email:
            return jsonify({"success": False, "error": "Email already subscribed"}), 400
        
        # Store email in database
        email_data = {
            "email": email,
            "source": "SanoURL",
            "subscribed_at": datetime.utcnow(),
            "ip_address": get_client_ip()
        }
        
        emails_collection.insert_one(email_data)
        
        return jsonify({
            "success": True,
            "message": "Successfully subscribed to newsletter"
        })
    
    except Exception as e:
        app.logger.error(f"Subscribe error: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred"}), 500


@app.route("/shorten", methods=['POST'])
def shorten_url():
    """Create a shortened URL"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        if not data:
            return jsonify({"success": False, "error": "No data received"}), 400
        
        original_url = data.get("url", "").strip()
        custom_code = data.get("custom_code", "").strip()
        turnstile_token = data.get("turnstile_token", "")

        # Verify Turnstile
        if not verify_turnstile(turnstile_token):
            return jsonify({"success": False, "error": "Verification failed. Please refresh and try again."}), 400

        if not original_url:
            return jsonify({"success": False, "error": "URL is required"}), 400
        
        # Validate URL
        if not is_valid_url(original_url):
            return jsonify({"success": False, "error": "Invalid URL format"}), 400
        
        # Add protocol if missing
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url
        
        # Handle custom code
        if custom_code:
            # Validate custom code format
            if not re.match(r'^[a-zA-Z0-9-_]{3,20}$', custom_code):
                return jsonify({"success": False, "error": "Custom code must be 3-20 alphanumeric characters"}), 400
            
            if urls_collection.find_one({"short_code": custom_code}):
                return jsonify({"success": False, "error": "Custom code already taken"}), 400
            short_code = custom_code
        else:
            short_code = generate_short_code()
        
        # Store in database
        url_data = {
            "original_url": original_url,
            "short_code": short_code,
            "created_at": datetime.utcnow(),
            "created_by_ip": get_client_ip(),
            "clicks": 0
        }
        
        urls_collection.insert_one(url_data)
        
        # Generate short URL
        short_url = request.host_url + short_code
        
        return jsonify({
            "success": True,
            "short_url": short_url,
            "short_code": short_code,
            "original_url": original_url
        })
    
    except Exception as e:
        app.logger.error(f"Shorten URL error: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred. Please try again."}), 500


@app.route("/<short_code>")
def redirect_to_url(short_code):
    """Redirect short code to original URL"""
    try:
        url_doc = urls_collection.find_one({"short_code": short_code})
        
        if not url_doc:
            return render_template('404.html'), 404
        
        # Increment click counter
        urls_collection.update_one(
            {"short_code": short_code},
            {
                "$inc": {"clicks": 1},
                "$set": {"last_accessed": datetime.utcnow()}
            }
        )
        
        return redirect(url_doc["original_url"], code=301)
    
    except Exception as e:
        app.logger.error(f"Redirect error: {str(e)}")
        return render_template('404.html'), 404


@app.route("/robots.txt")
def robots():
    """Serve robots.txt"""
    return app.send_static_file('robots.txt')


@app.route("/sitemap.xml")
def sitemap():
    """Generate sitemap.xml"""
    pages = []
    
    pages.append({
        'loc': 'https://sanourl.globsoft.tech/',
        'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
        'changefreq': 'daily',
        'priority': '1.0'
    })
    
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        sitemap_xml += '  <url>\n'
        sitemap_xml += f'    <loc>{page["loc"]}</loc>\n'
        sitemap_xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
        sitemap_xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        sitemap_xml += f'    <priority>{page["priority"]}</priority>\n'
        sitemap_xml += '  </url>\n'
    
    sitemap_xml += '</urlset>'
    
    response = make_response(sitemap_xml)
    response.headers['Content-Type'] = 'application/xml'
    return response


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    app.logger.error(f"Internal error: {str(e)}")
    return jsonify({"success": False, "error": "Internal server error"}), 500