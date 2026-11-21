"""Feasibility experiment E1 for driftcheck.
Part A: does subprocess.run(timeout=...) stop the child process?
Part B: do committed history rows survive when the process is killed (SIGKILL)?
"""
import os, sys, time, signal, sqlite3, subprocess, tempfile, textwrap

work = tempfile.mkdtemp()
fake = os.path.join(work, "fake_terraform.sh")
pidfile = os.path.join(work, "child.pid")
with open(fake, "w") as f:
    f.write(f"#!/bin/sh\necho $$ > {pidfile}\nsleep 30\nexit 0\n")
os.chmod(fake, 0o755)

print("Python", sys.version.split()[0], "| sqlite library", sqlite3.sqlite_version)

# ---- Part A
print("\n== Part A: timeout on a stuck child process ==")
start = time.monotonic()
timed_out = False
try:
    subprocess.run([fake], capture_output=True, timeout=2)
except subprocess.TimeoutExpired:
    timed_out = True
elapsed = time.monotonic() - start
pid = int(open(pidfile).read().strip())
try:
    os.kill(pid, 0); alive = True
except ProcessLookupError:
    alive = False
print(f"TimeoutExpired raised: {timed_out}")
print(f"elapsed seconds: {elapsed:.2f} (limit was 2)")
print(f"child pid {pid} still running after timeout: {alive}")

# ---- Part B
print("\n== Part B: history rows after the process is killed ==")
child_code = textwrap.dedent("""
    import sqlite3, sys, time
    con = sqlite3.connect(sys.argv[1])
    con.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, outcome TEXT)")
    with con:
        con.execute("INSERT INTO checks (outcome) VALUES ('committed row')")
    print("committed", flush=True)
    con.execute("INSERT INTO checks (outcome) VALUES ('uncommitted row')")
    print("inserted without commit", flush=True)
    time.sleep(30)
""")
results = []
for run in range(1, 6):
    db = os.path.join(work, f"history{run}.db")
    p = subprocess.Popen([sys.executable, "-c", child_code, db],
                         stdout=subprocess.PIPE, text=True)
    p.stdout.readline(); p.stdout.readline()   # wait for both lines
    p.send_signal(signal.SIGKILL); p.wait()
    con = sqlite3.connect(db)
    rows = [r[0] for r in con.execute("SELECT outcome FROM checks ORDER BY id")]
    con.close()
    results.append(rows)
    print(f"run {run}: child killed with SIGKILL, rows found after reopening: {rows}")
ok = all(r == ["committed row"] for r in results)
print("all 5 runs kept only the committed row:", ok)
