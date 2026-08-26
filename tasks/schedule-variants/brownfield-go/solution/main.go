package main

import (
	"encoding/json"
	"log"
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

const layout = "2006-01-02T15:04:05.000Z"

var (
	mu   sync.Mutex
	jobs = map[string]Job{
		"1": {
			ID:       "1",
			Name:     "backup",
			Schedule: Schedule{Kind: "once", At: "2030-01-01T00:00:00.000Z"},
		},
	}
	nextID   = 2
	sabotage = os.Getenv("LAB_SABOTAGE")
)

func parseInstant(value string) (time.Time, bool) {
	parsed, err := time.Parse(time.RFC3339Nano, value)
	return parsed.UTC(), err == nil
}

// canonical renders an instant in UTC with milliseconds, or "" when invalid.
func canonical(value string) string {
	parsed, ok := parseInstant(value)
	if !ok {
		return ""
	}
	return parsed.Format(layout)
}

func normalize(raw map[string]any) (Schedule, bool) {
	if len(raw) == 2 && raw["kind"] == "once" {
		at, ok := raw["at"].(string)
		if !ok {
			return Schedule{}, false
		}
		at = canonical(at)
		return Schedule{Kind: "once", At: at}, at != ""
	}
	missing := sabotage == "missing-error-branch" && len(raw) == 2
	if (len(raw) == 3 || missing) && raw["kind"] == "interval" {
		start, ok := raw["startAt"].(string)
		if !ok {
			return Schedule{}, false
		}
		start = canonical(start)
		every := 1
		if value, exists := raw["everyMinutes"]; exists {
			minutes, isNumber := value.(float64)
			if !isNumber || minutes != math.Trunc(minutes) || minutes <= 0 {
				return Schedule{}, false
			}
			every = int(minutes)
		} else if !missing {
			return Schedule{}, false
		}
		if start != "" {
			schedule := Schedule{
				Kind:         "interval",
				StartAt:      start,
				EveryMinutes: every,
			}
			return schedule, true
		}
	}
	return Schedule{}, false
}

// nextRun reports the next run and whether `after` was a valid instant.
func nextRun(schedule Schedule, after string) (any, bool) {
	moment, ok := parseInstant(after)
	if !ok {
		return nil, false
	}
	if schedule.Kind == "once" {
		at, _ := parseInstant(schedule.At)
		if at.After(moment) {
			return schedule.At, true
		}
		return nil, true
	}
	start, _ := parseInstant(schedule.StartAt)
	if moment.Before(start) {
		return schedule.StartAt, true
	}
	step := time.Duration(schedule.EveryMinutes) * time.Minute
	periods := int64(moment.Sub(start) / step)
	if sabotage != "off-by-one" {
		periods++
	}
	return start.Add(time.Duration(periods) * step).Format(layout), true
}

// rejectStatus is the status used to reject a malformed request.
func rejectStatus() int {
	if sabotage == "wrong-status-code" {
		return http.StatusUnprocessableEntity
	}
	return http.StatusBadRequest
}

func allowed(raw map[string]any) bool {
	for key := range raw {
		if key != "name" && key != "schedule" {
			return false
		}
	}
	return true
}

func send(w http.ResponseWriter, status int, value any) {
	data, err := json.Marshal(value)
	if err != nil {
		http.Error(w, "encoding failed", http.StatusInternalServerError)
		return
	}
	w.Header().Set("content-type", "application/json")
	w.Header().Set("content-length", strconv.Itoa(len(data)))
	w.WriteHeader(status)
	_, _ = w.Write(data)
}

func fail(w http.ResponseWriter, status int, message string) {
	send(w, status, map[string]string{"error": message})
}

func createJob(w http.ResponseWriter, r *http.Request) {
	var body map[string]any
	if json.NewDecoder(r.Body).Decode(&body) != nil || !allowed(body) {
		fail(w, rejectStatus(), "invalid job")
		return
	}
	name, named := body["name"].(string)
	raw, isObject := body["schedule"].(map[string]any)
	schedule, valid := normalize(raw)
	if !named || name == "" || !isObject || !valid {
		fail(w, rejectStatus(), "invalid job")
		return
	}
	job := Job{ID: strconv.Itoa(nextID), Name: name, Schedule: schedule}
	nextID++
	jobs[job.ID] = job
	send(w, http.StatusCreated, job)
}

func patchJob(w http.ResponseWriter, r *http.Request, job Job) {
	var body map[string]any
	if json.NewDecoder(r.Body).Decode(&body) != nil || len(body) == 0 || !allowed(body) {
		fail(w, rejectStatus(), "invalid patch")
		return
	}
	name := job.Name
	if value, exists := body["name"]; exists {
		named := false
		name, named = value.(string)
		if !named || name == "" {
			fail(w, rejectStatus(), "invalid patch")
			return
		}
	}
	schedule := job.Schedule
	if value, exists := body["schedule"]; exists {
		raw, isObject := value.(map[string]any)
		valid := false
		schedule, valid = normalize(raw)
		if !isObject || !valid {
			fail(w, rejectStatus(), "invalid patch")
			return
		}
		// The sabotage leaves fields of the old schedule behind on a kind switch.
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
	jobs[job.ID] = job
	send(w, http.StatusOK, job)
}

func serveNextRun(w http.ResponseWriter, r *http.Request, job Job) {
	result, valid := nextRun(job.Schedule, r.URL.Query().Get("after"))
	if !valid {
		fail(w, rejectStatus(), "invalid after")
		return
	}
	send(w, http.StatusOK, map[string]any{"nextRun": result})
}

func handler(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 1 || parts[0] != "jobs" || len(parts) > 3 {
		fail(w, http.StatusNotFound, "not found")
		return
	}
	id := ""
	if len(parts) >= 2 {
		id = parts[1]
	}
	next := len(parts) == 3 && parts[2] == "next"
	mu.Lock()
	defer mu.Unlock()
	if r.Method == http.MethodPost && id == "" {
		createJob(w, r)
		return
	}
	if id == "" {
		fail(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	job, found := jobs[id]
	if !found {
		fail(w, http.StatusNotFound, "not found")
		return
	}
	switch {
	case r.Method == http.MethodGet && next:
		serveNextRun(w, r, job)
	case r.Method == http.MethodGet:
		send(w, http.StatusOK, job)
	case r.Method == http.MethodPatch && !next:
		patchJob(w, r, job)
	default:
		fail(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func env(key string, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func main() {
	http.HandleFunc("/jobs", handler)
	http.HandleFunc("/jobs/", handler)
	if err := http.ListenAndServe(":"+env("PORT", "8080"), nil); err != nil {
		log.Fatal(err)
	}
}
