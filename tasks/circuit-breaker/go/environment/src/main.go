package main

import (
	"encoding/json"
	"fmt"
	"os"
)

type decision struct {
	Target   string `json:"target"`
	State    string `json:"state"`
	Admitted bool   `json:"admitted"`
	Recorded string `json:"recorded"`
}

type summary struct {
	Target   string `json:"target"`
	State    string `json:"state"`
	Failures int    `json:"failures"`
}

type result struct {
	Decisions []decision `json:"decisions"`
	Targets   []summary  `json:"targets"`
}

func run(input document) result {
	item := newBreaker()
	seen := []string{}
	decisions := []decision{}
	for _, entry := range input.Calls {
		known := false
		for _, name := range seen {
			if name == entry.Target {
				known = true
				break
			}
		}
		if !known {
			seen = append(seen, entry.Target)
		}
		observed := observe(item, entry.At, input.Config)
		if !admit(item, observed, input.Config) {
			decisions = append(decisions, decision{
				Target:   entry.Target,
				State:    observed,
				Admitted: false,
				Recorded: "rejected",
			})
			continue
		}
		outcome := classify(entry.Outcome, input.Config.FailureStatuses)
		record(item, observed, outcome, entry.At, input.Config)
		decisions = append(decisions, decision{
			Target:   entry.Target,
			State:    observed,
			Admitted: true,
			Recorded: outcome,
		})
	}
	targets := []summary{}
	for _, name := range seen {
		targets = append(targets, summary{
			Target:   name,
			State:    item.state,
			Failures: item.failures,
		})
	}
	return result{Decisions: decisions, Targets: targets}
}

func main() {
	var input document
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoded, err := json.Marshal(run(input))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}
