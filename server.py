#!/usr/bin/env python3

import http.server, socketserver, json, os, time, urllib.request
from urllib.parse import urlparse, parse_qs
from threading import Thread
from signal import pause
from gpiozero import RotaryEncoder
import csv
import random

WEBROOT = "/home/tekavou/website"
FACES_JSON = os.path.join(WEBROOT, "faces.json")
TTL = 600
DEBOUNCE = 0.5
face_idx = 0
_cache_t = 0
_cache_d = None
_last_time = 0

LAT, LON = 45.4615, -73.5464 # Enter your location coordinates here

encoder = RotaryEncoder(17, 27, max_steps=0)

def save_faces():
    with open(FACES_JSON, "r") as f:
        data = json.load(f)
    data["current"] = face_idx
    with open(FACES_JSON, "w") as f:
        json.dump(data, f)

def rotate(delta):
    global face_idx, _last_time
    now = time.time()
    if now - _last_time < DEBOUNCE:
        return
    _last_time = now

    with open(FACES_JSON) as f:
        data = json.load(f)

    faces = data["faces"]
    face_idx = (face_idx + delta) % len(faces)
    save_faces()
    print("Rotary →", "CW" if delta > 0 else "CCW", "→", faces[face_idx])

encoder.when_rotated_clockwise = lambda: rotate(1)
encoder.when_rotated_counter_clockwise = lambda: rotate(-1)
Thread(target=pause, daemon=True).start()

def fetch_weather():
    global _cache_t, _cache_d
    if time.time() - _cache_t < TTL:
        return _cache_d
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}&current_weather=true"
        f"&hourly=temperature_2m,weathercode&forecast_days=1"
        f"&timezone=America/Toronto"
    )
    with urllib.request.urlopen(url, timeout=4) as r:
        _cache_d = json.load(r)
        _cache_t = time.time()
        return _cache_d

def fetch_inspiration():
    csv_path = os.path.join(WEBROOT, "global/data/inspiration.csv")
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            quotes = [row["Quote"] for row in reader if row.get("Quote")]
            return {"quote": random.choice(quotes)} if quotes else {"quote": "No quotes found."}
    except Exception as e:
        return {"error": str(e)}

def fetch_fact():
    facts_path = os.path.join(WEBROOT, "global/data/facts.csv")
    try:
        with open(facts_path, encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines and lines[0].lower() == "facts":
                lines = lines[1:]
            return {"fact": random.choice(lines)} if lines else {"fact": "No facts found."}
    except Exception as e:
        return {"error": str(e)}

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/weather":
            try:
                data = fetch_weather()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_error(500, str(e))

        elif path == "/current_face":
            try:
                last = int(parse_qs(parsed.query).get("last", [-1])[0])

                with open(FACES_JSON) as f:
                    data = json.load(f)

                if data.get("current") != last:
                    response = data
                else:
                    timeout = 15
                    interval = 0.25
                    waited = 0
                    while waited < timeout:
                        time.sleep(interval)
                        waited += interval
                        with open(FACES_JSON) as f:
                            data = json.load(f)
                        if data.get("current") != last:
                            break
                    response = data

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                self.send_error(500, str(e))

        elif path == "/inspiration":
            data = fetch_inspiration()
            if "error" in data:
                self.send_error(500, data["error"])
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

        elif path == "/fact":
            data = fetch_fact()
            if "error" in data:
                self.send_error(500, data["error"])
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

        elif path == "/subscribers":
            try:
                subs_path = os.path.join(WEBROOT, "global/data/subscribers.json")
                with open(subs_path) as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_error(500, str(e))

        else:
            super().do_GET()

if __name__ == "__main__":
    os.chdir(WEBROOT)
    class ReusableTCP(socketserver.TCPServer): allow_reuse_address = True
    with ReusableTCP(("", 8000), Handler) as httpd:
        print("Serving at http://appleclock.local:8000")
        httpd.serve_forever()