import json, os, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

POD_NAME = os.getenv("POD_NAME", "unknown")
POD_NS = os.getenv("POD_NAMESPACE", "default")
PORT = int(os.getenv("PORT", "8080"))
DATA_DIR = os.getenv("DATA_DIR", "/data")
READY_DELAY = int(os.getenv("READY_DELAY", "3"))

STATE_PATH = os.path.join(DATA_DIR, "state.json")
start_ts = time.time()
ready_at = start_ts + READY_DELAY

state = {"counter": 0, "boot_time": int(start_ts), "pod": POD_NAME}

def log(msg):
  ts = time.strftime("%Y-%m-%d %H:%M:%S")
  print(f"{ts} [{POD_NS}/{POD_NAME}] {msg}", flush=True)

def load_state():
  global state
  try:
    if os.path.exists(STATE_PATH):
      with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
        state["pod"] = POD_NAME
        log(f"state loaded: {state}")
    else:
      log("state file not found, starting fresh")
  except Exception as e:
    log(f"state load error: {e}")

def save_state():
  os.makedirs(DATA_DIR, exist_ok=True)
  tmp = STATE_PATH + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False)
  os.replace(tmp, STATE_PATH)

class Handler(BaseHTTPRequestHandler):
  def _json(self, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    self.send_response(code)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, fmt, *args):
    pass

  def do_GET(self):
    parsed = urlparse(self.path)
    path = parsed.path

    if path == "/healthz":
      self._json(200, {"ok": True})
      return

    if path == "/readyz":
      if time.time() < ready_at:
        self._json(503, {"ready": False, "reason": "warming_up"})
        return
      try:
        save_state()
      except Exception as e:
        self._json(503, {"ready": False, "reason": f"cannot_write_state: {e}"})
        return
      self._json(200, {"ready": True})
      return

    if path == "/state":
      out = dict(state)
      out["uptime_s"] = int(time.time() - start_ts)
      out["pod"] = POD_NAME
      self._json(200, out)
      return

    out = dict(state)
    out["uptime_s"] = int(time.time() - start_ts)
    out["pod"] = POD_NAME
    out["namespace"] = POD_NS
    self._json(200, out)

  def do_POST(self):
    parsed = urlparse(self.path)
    if parsed.path == "/inc":
      state["counter"] = int(state.get("counter", 0)) + 1
      state["last_inc_ts"] = int(time.time())
      state["pod"] = POD_NAME
      save_state()
      log(f"INC -> counter={state['counter']}")
      self._json(200, {"ok": True, "counter": state["counter"], "pod": POD_NAME})
      return

    if parsed.path == "/burn":
      qs = parse_qs(parsed.query)
      ms = int(qs.get("ms", ["300"])[0])
      end = time.time() + (ms / 1000.0)
      x = 0
      while time.time() < end:
        x = (x * 33 + 7) % 1000003
      log(f"BURN {ms}ms done (x={x})")
      self._json(200, {"ok": True, "burn_ms": ms})
      return

    self._json(404, {"ok": False, "error": "not_found"})

if __name__ == "__main__":
  load_state()
  log(f"starting http on :{PORT}, data={STATE_PATH}, ready_delay={READY_DELAY}s")
  HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
