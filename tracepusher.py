import sys
import requests
import time
import secrets
import argparse

# This script is very simple. It does the equivalent of:
# curl -i -X POST http(s)://endpoint/v1/traces \
# -H "Content-Type: application/json" \
# -d @trace.json

#############################################################################
# USAGE
# python tracepusher.py -ep=http(s)://localhost:4318 -sen=serviceNameA -spn=spanX -dur=2
#############################################################################

parser = argparse.ArgumentParser()

# Notes:
# You can use either short or long (mix and match is OK)
# Hyphens are replaced with underscores hence for retrieval
# and leading hyphens are trimmed
# --span-name becomes args.span_name
# Retrieval also uses the second parameter
# Hence args.dry_run will work but args.d won't
parser.add_argument('-ep', '--endpoint', required=True)
parser.add_argument('-sen','--service-name', required=True)
parser.add_argument('-spn', '--span-name', required=True)
parser.add_argument('-dur', '--duration', required=True, type=int)
parser.add_argument('-dr','--dry-run','--dry', required=False, default="False")
parser.add_argument('-x', '--debug', required=False, default="False")
parser.add_argument('-ts', '--time-shift', required=False, default="False")
parser.add_argument('-ptid','--parent-trace-id', required=False, default="")
parser.add_argument('-tid', '--trace-id', required=False, default="")

args = parser.parse_args()

endpoint = args.endpoint
service_name = args.service_name
span_name = args.span_name
duration = args.duration
dry_run = args.dry_run
debug_mode = args.debug
time_shift = args.time_shift
parent_trace_id = args.parent_trace_id
trace_id = args.trace_id

# Debug mode required?
DEBUG_MODE = False
if debug_mode.lower() == "true":
   print("> Debug mode is ON")
   DEBUG_MODE = True

DRY_RUN = False
if dry_run.lower() == "true":
   print("> Dry run mode is ON. Nothing will actually be sent.")
   DRY_RUN = True

TIME_SHIFT = False
if time_shift.lower() == "true":
  print("> Time shift enabled. Will shift the start and end time back in time by DURATION seconds.")
  TIME_SHIFT = True

IS_CHILD_SPAN = False
if parent_trace_id != "":
  print(f"> Pushing a child (sub) span with parent trace id: {parent_trace_id}")
  IS_CHILD_SPAN = True

IS_PARENT_TRACE = False
if trace_id != "":
  print(f"> Received an incoming trace_id. This is a parent trace: {trace_id}")
  IS_PARENT_TRACE = True

if DEBUG_MODE:
  print(f"Endpoint: {endpoint}")
  print(f"Service Name: {service_name}")
  print(f"Span Name: {span_name}")
  print(f"Duration: {duration}")
  print(f"Dry Run: {type(dry_run)} = {dry_run}")
  print(f"Debug: {type(debug_mode)} = {debug_mode}")
  print(f"Time Shift: {type(time_shift)} = {time_shift}")
  print(f"Parent Trace ID: {parent_trace_id}")
  print(f"Trace ID: {trace_id}")

# Generate random chars for trace and span IDs
# of 32 chars and 16 chars respectively
# per secrets documentation
# each byte is converted to two hex digits
# hence this "appears" wrong by half but isn't
# If this is a child span, we already have a trace_id
# So do not generate
# If this is a parent trace, we already have an incoming trace_id
# So do not generate
if not IS_PARENT_TRACE:
  if not IS_CHILD_SPAN:
    trace_id = secrets.token_hex(16)
  else:
    # Use incoming parent_trace_id as the trace_id for this span
    trace_id = parent_trace_id

# Parent trace, child span or not, always generate a span ID
span_id = secrets.token_hex(8)

if DEBUG_MODE:
  if IS_PARENT_TRACE:
    print(f"This is a parent trace. An incoming trace_id has been provided")
  elif not IS_CHILD_SPAN:
    print("This is a standard trace (NOT a child span) so a trace_id was autogenerated by tracepusher")
  else:
    print("This is a child span. parent_trace_id was passed in by the user")
  print(f"Trace ID: {trace_id}")
  print(f"Span ID: {span_id}")

duration_nanos = duration * 1000000000
# get time now
time_now = time.time_ns()
# calculate future time by adding that many seconds
time_future = time_now + duration_nanos

# shift time_now and time_future back by duration 
if TIME_SHIFT:
   time_now = time_now - duration_nanos
   time_future = time_future - duration_nanos

if DEBUG_MODE:
   print(f"Time shifted? {TIME_SHIFT}")
   print(f"Time now: {time_now}")
   print(f"Time future: {time_future}")

trace = {
 "resourceSpans": [
   {
     "resource": {
       "attributes": [
         {
           "key": "service.name",
           "value": {
             "stringValue": service_name
           }
         }
       ]
     },
     "scopeSpans": [
       {
         "scope": {
           "name": "manual-test"
         },
         "spans": [
           {
             "traceId": trace_id,
             "spanId": span_id,
             "name": span_name,
             "kind": "SPAN_KIND_INTERNAL",
             "start_time_unix_nano": time_now,
             "end_time_unix_nano": time_future,
             "droppedAttributesCount": 0,
             "events": [],
             "droppedEventsCount": 0,
             "status": {
               "code": 1
             }
           }
         ]
       }
     ]
   }
 ]
}

if DEBUG_MODE:
   print("Trace:")
   print(trace)

if DRY_RUN:
   print(f"Collector URL: {endpoint}. Service Name: {service_name}. Span Name: {span_name}. Trace Length (seconds): {duration}")
   # Only print if also not running in DEBUG_MODE
   # Otherwise we get a double print
   if not DEBUG_MODE:
     print("Trace:")
     print(trace)
   
if not DRY_RUN:
  resp = requests.post(f"{endpoint}/v1/traces", headers={ "Content-Type": "application/json" }, json=trace)
  print(resp)