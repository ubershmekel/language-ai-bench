package main

import (
	"encoding/json"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Schedule struct {
	Kind         string `json:"kind"`
	At           string `json:"at,omitempty"`
	StartAt      string `json:"startAt,omitempty"`
	EveryMinutes int    `json:"everyMinutes,omitempty"`
}
type Job struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Schedule Schedule `json:"schedule"`
}

var mu sync.Mutex
var jobs = map[string]Job{"1": {ID: "1", Name: "backup", Schedule: Schedule{Kind: "once", At: "2030-01-01T00:00:00.000Z"}}}
var nextID = 2
var sabotage = os.Getenv("LAB_SABOTAGE")

func parseInstant(v string) (time.Time, bool) {
	t, e := time.Parse(time.RFC3339Nano, v)
	return t.UTC(), e == nil
}
func canonical(v string) string {
	t, ok := parseInstant(v)
	if !ok {
		return ""
	}
	return t.Format("2006-01-02T15:04:05.000Z")
}
func normalize(x map[string]any) (Schedule, bool) {
	if len(x) == 2 && x["kind"] == "once" {
		at, ok := x["at"].(string)
		if !ok {
			return Schedule{}, false
		}
		at = canonical(at)
		return Schedule{Kind: "once", At: at}, at != ""
	}
	missing := sabotage == "missing-error-branch" && len(x) == 2
	if (len(x) == 3 || missing) && x["kind"] == "interval" {
		start, ok := x["startAt"].(string)
		if !ok {
			return Schedule{}, false
		}
		start = canonical(start)
		every := 1
		if v, exists := x["everyMinutes"]; exists {
			n, ok := v.(float64)
			if !ok || n != math.Trunc(n) || n <= 0 {
				return Schedule{}, false
			}
			every = int(n)
		} else if !missing {
			return Schedule{}, false
		}
		if start != "" {
			return Schedule{Kind: "interval", StartAt: start, EveryMinutes: every}, true
		}
	}
	return Schedule{}, false
}
func nextRun(s Schedule, v string) (any, bool) {
	after, ok := parseInstant(v)
	if !ok {
		return nil, false
	}
	if s.Kind == "once" {
		at, _ := parseInstant(s.At)
		if at.After(after) {
			return s.At, true
		}
		return nil, true
	}
	start, _ := parseInstant(s.StartAt)
	if after.Before(start) {
		return s.StartAt, true
	}
	step := time.Duration(s.EveryMinutes) * time.Minute
	periods := int64(after.Sub(start) / step)
	if sabotage != "off-by-one" {
		periods++
	}
	return start.Add(time.Duration(periods) * step).Format("2006-01-02T15:04:05.000Z"), true
}
func bad() int {
	if sabotage == "wrong-status-code" {
		return 422
	}
	return 400
}
func allowed(x map[string]any) bool {
	for k := range x {
		if k != "name" && k != "schedule" {
			return false
		}
	}
	return true
}
func send(w http.ResponseWriter, s int, v any) {
	d, _ := json.Marshal(v)
	w.Header().Set("content-type", "application/json")
	w.Header().Set("content-length", strconv.Itoa(len(d)))
	w.WriteHeader(s)
	w.Write(d)
}
func handler(w http.ResponseWriter, r *http.Request) {
	p := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(p) < 1 || p[0] != "jobs" || len(p) > 3 {
		send(w, 404, map[string]string{"error": "not found"})
		return
	}
	id := ""
	if len(p) >= 2 {
		id = p[1]
	}
	next := len(p) == 3 && p[2] == "next"
	mu.Lock()
	defer mu.Unlock()
	if r.Method == "POST" && id == "" {
		var x map[string]any
		if json.NewDecoder(r.Body).Decode(&x) != nil || len(x) > 2 || !allowed(x) {
			send(w, bad(), map[string]string{"error": "invalid job"})
			return
		}
		name, ok := x["name"].(string)
		raw, ok2 := x["schedule"].(map[string]any)
		schedule, ok3 := normalize(raw)
		if !ok || name == "" || !ok2 || !ok3 {
			send(w, bad(), map[string]string{"error": "invalid job"})
			return
		}
		job := Job{ID: strconv.Itoa(nextID), Name: name, Schedule: schedule}
		nextID++
		jobs[job.ID] = job
		send(w, 201, job)
		return
	}
	if id == "" {
		send(w, 405, map[string]string{"error": "method not allowed"})
		return
	}
	job, ok := jobs[id]
	if !ok {
		send(w, 404, map[string]string{"error": "not found"})
		return
	}
	if r.Method == "GET" && next {
		result, valid := nextRun(job.Schedule, r.URL.Query().Get("after"))
		if !valid {
			send(w, bad(), map[string]string{"error": "invalid after"})
			return
		}
		send(w, 200, map[string]any{"nextRun": result})
		return
	}
	if r.Method == "GET" && !next {
		send(w, 200, job)
		return
	}
	if r.Method == "PATCH" && !next {
		var x map[string]any
		if json.NewDecoder(r.Body).Decode(&x) != nil || len(x) == 0 || len(x) > 2 || !allowed(x) {
			send(w, bad(), map[string]string{"error": "invalid patch"})
			return
		}
		name := job.Name
		if v, exists := x["name"]; exists {
			var valid bool
			name, valid = v.(string)
			if !valid || name == "" {
				send(w, bad(), map[string]string{"error": "invalid patch"})
				return
			}
		}
		schedule := job.Schedule
		if v, exists := x["schedule"]; exists {
			raw, valid := v.(map[string]any)
			var good bool
			schedule, good = normalize(raw)
			if !valid || !good {
				send(w, bad(), map[string]string{"error": "invalid patch"})
				return
			}
			if sabotage == "unhandled-concurrent-update" {
				if schedule.At == "" {
					schedule.At = job.Schedule.At
				}
				if schedule.StartAt == "" {
					schedule.StartAt = job.Schedule.StartAt
				}
			}
		}
		job.Name = name
		job.Schedule = schedule
		jobs[id] = job
		send(w, 200, job)
		return
	}
	send(w, 405, map[string]string{"error": "method not allowed"})
}
func main() {
	http.HandleFunc("/jobs", handler)
	http.HandleFunc("/jobs/", handler)
	http.ListenAndServe(":"+env("PORT", "8080"), nil)
}
func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
