package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Schedule struct {
	Kind string `json:"kind"`
	At   string `json:"at,omitempty"`
}

type Job struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Schedule Schedule `json:"schedule"`
}

var (
	mu   sync.Mutex
	jobs = map[string]Job{
		"1": {
			ID:       "1",
			Name:     "backup",
			Schedule: Schedule{Kind: "once", At: "2030-01-01T00:00:00.000Z"},
		},
	}
	nextID = 2
)

// canonical renders an RFC 3339 instant in UTC with milliseconds, or "" when
// the text is not a valid instant.
func canonical(value string) string {
	parsed, err := time.Parse(time.RFC3339Nano, value)
	if err != nil {
		return ""
	}
	return parsed.UTC().Format("2006-01-02T15:04:05.000Z")
}

func normalize(raw map[string]any) (Schedule, bool) {
	if len(raw) != 2 || raw["kind"] != "once" {
		return Schedule{}, false
	}
	at, ok := raw["at"].(string)
	if !ok {
		return Schedule{}, false
	}
	at = canonical(at)
	return Schedule{Kind: "once", At: at}, at != ""
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
		fail(w, http.StatusBadRequest, "invalid job")
		return
	}
	name, named := body["name"].(string)
	raw, isObject := body["schedule"].(map[string]any)
	schedule, valid := normalize(raw)
	if !named || name == "" || !isObject || !valid {
		fail(w, http.StatusBadRequest, "invalid job")
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
		fail(w, http.StatusBadRequest, "invalid patch")
		return
	}
	name := job.Name
	if value, present := body["name"]; present {
		named := false
		name, named = value.(string)
		if !named || name == "" {
			fail(w, http.StatusBadRequest, "invalid patch")
			return
		}
	}
	schedule := job.Schedule
	if value, present := body["schedule"]; present {
		raw, isObject := value.(map[string]any)
		valid := false
		schedule, valid = normalize(raw)
		if !isObject || !valid {
			fail(w, http.StatusBadRequest, "invalid patch")
			return
		}
	}
	job.Name = name
	job.Schedule = schedule
	jobs[job.ID] = job
	send(w, http.StatusOK, job)
}

func nextRun(w http.ResponseWriter, r *http.Request, job Job) {
	after := canonical(r.URL.Query().Get("after"))
	if after == "" {
		fail(w, http.StatusBadRequest, "invalid after")
		return
	}
	var result any
	if job.Schedule.At > after {
		result = job.Schedule.At
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
		nextRun(w, r, job)
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
