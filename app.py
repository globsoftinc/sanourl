from flask import Flask, render_template, request, jsonify, redirect
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


def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_short_code(length=6):
    """Generate a random short code for URLs"""
    characters = string.ascii_letters + string.digits
    while True:
        short_code = ''.join(random.choice(characters) for _ in range(length))
        if not urls_collection.find_one({"short_code": short_code}):
            return short_code

def verify_turnstile(token):
    """Verify Cloudflare Turnstile token"""
    if not token:
        return False
    
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': turnstile_secret,
                'response': token
            },
            timeout=5
        )
        return response.json().get('success', False)
    except:
        return False

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html', turnstile_site_key=turnstile_site_key)


@app.route("/subscribe", methods=['POST'])
def subscribe():
    """Subscribe email to newsletter"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        turnstile_token = data.get("turnstile_token", "")
        
        if not verify_turnstile(turnstile_token):
            return jsonify({"success": False, "error": "Verification failed"}), 400

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
            "subscribed_at": datetime.now()
        }
        
        emails_collection.insert_one(email_data)
        
        return jsonify({
            "success": True,
            "message": "Successfully subscribed to newsletter"
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/shorten", methods=['POST'])
def shorten_url():
    """Create a shortened URL"""
    try:
        data = request.get_json() if request.is_json else request.form
        original_url = data.get("url")
        custom_code = data.get("custom_code", "").strip()
        turnstile_token = data.get("turnstile_token", "")

        if not verify_turnstile(turnstile_token):
            return jsonify({"success": False, "error": "Verification failed"}), 400

        if not original_url:
            return jsonify({"success": False, "error": "URL is required"}), 400
        
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'https://' + original_url
        
        if custom_code:
            if urls_collection.find_one({"short_code": custom_code}):
                return jsonify({"success": False, "error": "Custom code already taken"}), 400
            short_code = custom_code
        else:
            short_code = generate_short_code()
        
        url_data = {
            "original_url": original_url,
            "short_code": short_code,
            "created_at": datetime.now()
        }
        
        urls_collection.insert_one(url_data)
        
        short_url = request.host_url + short_code
        
        return jsonify({
            "success": True,
            "short_url": short_url,
            "short_code": short_code,
            "original_url": original_url
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/<short_code>")
def redirect_to_url(short_code):
    """Redirect short code to original URL"""
    url_doc = urls_collection.find_one({"short_code": short_code})
    
    if not url_doc:
        return render_template('404.html'), 404
    
    return redirect(url_doc["original_url"])


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route("/robots.txt")
def robots():
    """Serve robots.txt"""
    return app.send_static_file('robots.txt')


@app.route("/sitemap.xml")
def sitemap():
    """Generate sitemap.xml"""
    pages = []
    
    # Add static pages
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