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

var mu sync.Mutex
var records = map[string]*Record{"1": {Task: Task{ID: "1", Title: "calibrate"}, Version: 1}}
var next = 2
var sabotage = os.Getenv("LAB_SABOTAGE")

func etag(x *Record) string {
	if sabotage == "off-by-one" {
		return `"v` + strconv.Itoa(x.Version) + `"`
	}
	b, _ := json.Marshal(x.Task)
	sum := sha256.Sum256(append(b, []byte(":"+strconv.Itoa(x.Version))...))
	return `"` + hex.EncodeToString(sum[:])[:16] + `"`
}
func send(w http.ResponseWriter, s int, v any, t string) {
	w.Header().Set("content-type", "application/json")
	if t != "" {
		w.Header().Set("etag", t)
	}
	w.WriteHeader(s)
	if v != nil {
		_ = json.NewEncoder(w).Encode(v)
	}
}
func handler(w http.ResponseWriter, r *http.Request) {
	p := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(p) < 1 || p[0] != "tasks" || len(p) > 2 {
		send(w, 404, nil, "")
		return
	}
	id := ""
	if len(p) == 2 {
		id = p[1]
	}
	if r.Method == "GET" && id == "" {
		mu.Lock()
		out := []Task{}
		for _, x := range records {
			out = append(out, x.Task)
		}
		mu.Unlock()
		send(w, 200, out, "")
		return
	}
	if r.Method == "POST" && id == "" {
		var t Task
		json.NewDecoder(r.Body).Decode(&t)
		mu.Lock()
		t.ID = strconv.Itoa(next)
		next++
		x := &Record{Task: t, Version: 1}
		records[t.ID] = x
		mu.Unlock()
		send(w, 201, t, etag(x))
		return
	}
	mu.Lock()
	x := records[id]
	mu.Unlock()
	if x == nil {
		send(w, 404, nil, "")
		return
	}
	if r.Method == "GET" {
		send(w, 200, x.Task, etag(x))
		return
	}
	if r.Method == "PUT" || r.Method == "PATCH" || r.Method == "DELETE" {
		h := r.Header.Get("if-match")
		if h == "" {
			send(w, 428, nil, "")
			return
		}
		if h != etag(x) && sabotage != "missing-error-branch" {
			s := 412
			if sabotage == "wrong-status-code" {
				s = 409
			}
			send(w, s, nil, "")
			return
		}
	}
	if r.Method == "DELETE" {
		mu.Lock()
		delete(records, id)
		mu.Unlock()
		send(w, 204, nil, "")
		return
	}
	if r.Method == "PUT" || r.Method == "PATCH" {
		before := etag(x)
		var in Task
		if r.Method == "PATCH" {
			var patch struct {
				Title *string `json:"title"`
				Done  *bool   `json:"done"`
			}
			json.NewDecoder(r.Body).Decode(&patch)
			in = x.Task
			if patch.Title != nil {
				in.Title = *patch.Title
			}
			if patch.Done != nil {
				in.Done = *patch.Done
			}
		} else {
			json.NewDecoder(r.Body).Decode(&in)
		}
		if sabotage == "unhandled-concurrent-update" {
			time.Sleep(80 * time.Millisecond)
		}
		mu.Lock()
		defer mu.Unlock()
		cur := records[id]
		if sabotage != "unhandled-concurrent-update" && sabotage != "missing-error-branch" && (cur == nil || etag(cur) != before) {
			s := 412
			if sabotage == "wrong-status-code" {
				s = 409
			}
			send(w, s, nil, "")
			return
		}
		in.ID = id
		x.Task = in
		if sabotage != "off-by-one" {
			x.Version++
		}
		records[id] = x
		send(w, 200, x.Task, etag(x))
		return
	}
	send(w, 405, nil, "")
}
func main() {
	http.HandleFunc("/tasks", handler)
	http.HandleFunc("/tasks/", handler)
	if err := http.ListenAndServe(":"+env("PORT", "8080"), nil); err != nil {
		log.Fatal(err)
	}
}
func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
