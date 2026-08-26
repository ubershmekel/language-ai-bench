package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
)

type Task struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Done  bool   `json:"done"`
}

var (
	mu    sync.Mutex
	tasks = map[string]Task{"1": {ID: "1", Title: "calibrate"}}
	next  = 2
)

func send(w http.ResponseWriter, status int, v any) {
	w.Header().Set("content-type", "application/json")
	w.WriteHeader(status)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}

func handler(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 1 || parts[0] != "tasks" || len(parts) > 2 {
		send(w, http.StatusNotFound, map[string]string{"error": "not found"})
		return
	}
	id := ""
	if len(parts) == 2 {
		id = parts[1]
	}
	mu.Lock()
	defer mu.Unlock()
	if r.Method == http.MethodGet && id == "" {
		out := []Task{}
		for _, t := range tasks {
			out = append(out, t)
		}
		send(w, http.StatusOK, out)
		return
	}
	if r.Method == http.MethodPost && id == "" {
		// The body is decoded on a best-effort basis and never validated.
		var in Task
		_ = json.NewDecoder(r.Body).Decode(&in)
		in.ID = strconv.Itoa(next)
		next++
		tasks[in.ID] = in
		send(w, http.StatusCreated, in)
		return
	}
	old, ok := tasks[id]
	if !ok {
		send(w, http.StatusNotFound, map[string]string{"error": "not found"})
		return
	}
	switch r.Method {
	case http.MethodGet:
		send(w, http.StatusOK, old)
	case http.MethodDelete:
		delete(tasks, id)
		send(w, http.StatusNoContent, nil)
	case http.MethodPut, http.MethodPatch:
		in := old
		if r.Method == http.MethodPatch {
			var patch struct {
				Title *string `json:"title"`
				Done  *bool   `json:"done"`
			}
			_ = json.NewDecoder(r.Body).Decode(&patch)
			if patch.Title != nil {
				in.Title = *patch.Title
			}
			if patch.Done != nil {
				in.Done = *patch.Done
			}
		} else {
			in = Task{}
			_ = json.NewDecoder(r.Body).Decode(&in)
		}
		in.ID = id
		tasks[id] = in
		send(w, http.StatusOK, in)
	default:
		send(w, http.StatusMethodNotAllowed, nil)
	}
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
