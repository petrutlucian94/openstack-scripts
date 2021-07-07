import sys
import time

retry_interval = 1

if len(sys.argv) != 2:
    print("Usage: %s <pipe_name>" % sys.argv[0])
    exit(1)

pipe_name = sys.argv[1]
if not pipe_name.startswith(r"\\.\pipe"):
    pipe_name = r"\\.\pipe\%s" % pipe_name

def read_pipe():
    with open(pipe_name, 'r') as f:
        while True:
            sys.stdout.write(f.read(1))

while True:
    try:
        read_pipe()
    except Exception as ex:
        print("Got exception while reading pipe: %s" % ex)
        print("Retrying in %s seconds." % retry_interval)
        time.sleep(retry_interval)
