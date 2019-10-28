# Script to convert from OCaml CTF format to Chrome's catapult format, used in chrome://tracing
import json
import sys
import babeltrace as bt

def event_to_catapult(ev):
    out = {}
    out['ts'] = "{}.{:03d}".format(ev['timestamp'] // 1000, ev['timestamp'] % 1000)
    out['pid'] = ev['pid']
    if ev['id'] == 0:
        out['ph'] = 'B'
        out['name'] = ev['phase']
    if ev['id'] == 1:
        out['ph'] = 'E'
        out['name'] = ev['phase']
    if ev['id'] == 2:
        out['args'] = {'value': ev['count']}
        out['name'] = ev['kind']
        out['ph'] = 'C'
    if ev['id'] == 3:
        out['args'] = {'value': ev['count']}
        out['name'] = ev['bucket']
        out['ph'] = 'C'
    if ev['id'] == 4:
       out['ph'] = 'X'
       out['name'] = 'eventlog/flush'
       out['dur'] = "{}.{:03d}".format(ev['duration'] // 1000, ev['duration'] % 1000)
    return out

def main():
    if len(sys.argv) != 3:
        print("usage: ./ctf_to_catapult.py trace_directory out.json")
        exit(0)
    dir = sys.argv[1]
    tr = bt.TraceCollection()
    tr.add_trace(dir, 'ctf')
    catapult_objects = list()
    for event in tr.events:
        if event['id'] <= 4:
            catapult_objects.append(event_to_catapult(event))
    catapult = {
        'displayTimeUnit': 'ns',
        'traceEvents': catapult_objects
    }
    with open(sys.argv[2], "w") as out:
        out.write(json.dumps(catapult))

if __name__ == '__main__':
    main()
