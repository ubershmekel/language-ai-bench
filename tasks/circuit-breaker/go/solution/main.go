package main

import (
	"encoding/json"
	"fmt"
	"os"
	"slices"
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

func run(value any) (result, error) {
	input, err := parseDocument(value)
	if err != nil {
		return result{}, err
	}
	settings, err := parseConfig(input.Config)
	if err != nil {
		return result{}, err
	}
	breakers := map[string]*breaker{}
	decisions := []decision{}
	previous := 0
	for _, item := range input.Calls {
		entry, err := parseCall(item, previous)
		if err != nil {
			return result{}, err
		}
		previous = entry.At
		outcome, err := classify(entry.Outcome, settings.FailureStatuses)
		if err != nil {
			return result{}, err
		}
		key := entry.Target
		if os.Getenv("LAB_SABOTAGE") == "global-state" {
			key = ""
		}
		current, present := breakers[key]
		if !present {
			current = newBreaker()
			breakers[key] = current
		}
		observed := observe(current, entry.At, settings)
		if !admit(current, observed, settings) {
			decisions = append(decisions, decision{
				Target:   entry.Target,
				State:    observed,
				Admitted: false,
				Recorded: "rejected",
			})
			continue
		}
		record(current, observed, outcome, entry.At, settings)
		decisions = append(decisions, decision{
			Target:   entry.Target,
			State:    observed,
			Admitted: true,
			Recorded: outcome,
		})
	}
	names := make([]string, 0, len(breakers))
	for name := range breakers {
		names = append(names, name)
	}
	slices.Sort(names)
	targets := make([]summary, 0, len(names))
	for _, name := range names {
		targets = append(targets, summary{
			Target:   name,
			State:    breakers[name].state,
			Failures: breakers[name].failures,
		})
	}
	return result{Decisions: decisions, Targets: targets}, nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	output, err := run(value)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoded, err := json.Marshal(output)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}
