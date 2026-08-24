#!/usr/bin/env python3
"""Mechanically extract diagnostic -> next edit at location -> resolution events."""
import argparse,json,pathlib,statistics
p=argparse.ArgumentParser();p.add_argument("events");p.add_argument("--output");a=p.parse_args();events=[json.loads(x) for x in pathlib.Path(a.events).read_text().splitlines() if x.strip()];found=[]
for pos,event in enumerate(events):
    if event.get("kind")!="diagnostic" or not event.get("diagnostic_id") or not event.get("location"):continue
    diag,loc,tool=event["diagnostic_id"],event["location"],event.get("tool");edit=None
    for later in events[pos+1:]:
        if edit is None and later.get("kind")=="edit" and loc in later.get("locations",[]):edit=later
        if edit is not None and later.get("kind")=="diagnostic" and later.get("tool")==tool and diag not in later.get("active_diagnostic_ids",[]):
            found.append({"diagnostic_id":diag,"location":loc,"emitted_event_index":event["index"],"edit_event_index":edit["index"],"resolved_event_index":later["index"],"steps_to_resolution":later["index"]-event["index"]});break
edits=sum(e.get("kind")=="edit" for e in events);summary={"feedback_to_fix_events":found,"count":len(found),"resolved_diagnostics_per_edit":len(found)/edits if edits else 0,"median_steps_to_resolution":statistics.median([x["steps_to_resolution"] for x in found]) if found else None};text=json.dumps(summary,indent=2);print(text)
if a.output:pathlib.Path(a.output).write_text(text+"\n")

