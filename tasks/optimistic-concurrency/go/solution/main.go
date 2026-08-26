package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Task struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Done  bool   `json:"done"`
}

type Record struct {
	Task    Task
	Version int
}

var (
	mu      sync.Mutex
	records = map[string]*Record{
		"1": {Task: Task{ID: "1", Title: "calibrate"}, Version: 1},
	}
	next     = 2
	sabotage = os.Getenv("LAB_SABOTAGE")
)

func etag(record *Record) string {
	if sabotage == "off-by-one" {
		return `"v` + strconv.Itoa(record.Version) + `"`
	}
	encoded, _ := json.Marshal(record.Task)
	version := []byte(":" + strconv.Itoa(record.Version))
	sum := sha256.Sum256(append(encoded, version...))
	return `"` + hex.EncodeToString(sum[:])[:16] + `"`
}

func send(w http.ResponseWriter, status int, value any, tag string) {
	w.Header().Set("content-type", "application/json")
	if tag != "" {
		w.Header().Set("etag", tag)
	}
	w.WriteHeader(status)
	if value != nil {
		_ = json.NewEncoder(w).Encode(value)
	}
}

// conflictStatus is the rejection status for a failed precondition.
func conflictStatus() int {
	if sabotage == "wrong-status-code" {
		return http.StatusConflict
	}
	return http.StatusPreconditionFailed
}

func handler(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 1 || parts[0] != "tasks" || len(parts) > 2 {
		send(w, http.StatusNotFound, nil, "")
		return
	}
	id := ""
	if len(parts) == 2 {
		id = parts[1]
	}
	if r.Method == http.MethodGet && id == "" {
		mu.Lock()
		out := []Task{}
		for _, record := range records {
			out = append(out, record.Task)
		}
		mu.Unlock()
		send(w, http.StatusOK, out, "")
		return
	}
	if r.Method == http.MethodPost && id == "" {
		var task Task
		_ = json.NewDecoder(r.Body).Decode(&task)
		mu.Lock()
		task.ID = strconv.Itoa(next)
		next++
		record := &Record{Task: task, Version: 1}
		records[task.ID] = record
		mu.Unlock()
		send(w, http.StatusCreated, task, etag(record))
		return
	}
	mu.Lock()
	record := records[id]
	mu.Unlock()
	if record == nil {
		send(w, http.StatusNotFound, nil, "")
		return
	}
	if r.Method == http.MethodGet {
		send(w, http.StatusOK, record.Task, etag(record))
		return
	}
	switch r.Method {
	case http.MethodPut, http.MethodPatch, http.MethodDelete:
		ifMatch := r.Header.Get("if-match")
		if ifMatch == "" {
			send(w, http.StatusPreconditionRequired, nil, "")
			return
		}
		if ifMatch != etag(record) && sabotage != "missing-error-branch" {
			send(w, conflictStatus(), nil, "")
			return
		}
	}
	if r.Method == http.MethodDelete {
		mu.Lock()
		delete(records, id)
		mu.Unlock()
		send(w, http.StatusNoContent, nil, "")
		return
	}
	if r.Method == http.MethodPut || r.Method == http.MethodPatch {
		before := etag(record)
		var in Task
		if r.Method == http.MethodPatch {
			var patch struct {
				Title *string `json:"title"`
				Done  *bool   `json:"done"`
			}
			_ = json.NewDecoder(r.Body).Decode(&patch)
			in = record.Task
			if patch.Title != nil {
				in.Title = *patch.Title
			}
			if patch.Done != nil {
				in.Done = *patch.Done
			}
		} else {
			_ = json.NewDecoder(r.Body).Decode(&in)
		}
		if sabotage == "unhandled-concurrent-update" {
			time.Sleep(80 * time.Millisecond)
		}
		mu.Lock()
		defer mu.Unlock()
		current := records[id]
		stale := current == nil || etag(current) != before
		if sabotage != "unhandled-concurrent-update" &&
			sabotage != "missing-error-branch" && stale {
			send(w, conflictStatus(), nil, "")
			return
		}
		in.ID = id
		record.Task = in
		if sabotage != "off-by-one" {
			record.Version++
		}
		records[id] = record
		send(w, http.StatusOK, record.Task, etag(record))
		return
	}
	send(w, http.StatusMethodNotAllowed, nil, "")
}

func env(key string, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func main() {
	http.HandleFunc("/tasks", handler)
	http.HandleFunc("/tasks/", handler)
	if err := http.ListenAndServe(":"+env("PORT", "8080"), nil); err != nil {
		log.Fatal(err)
	}
}
