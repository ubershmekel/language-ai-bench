package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

type failure struct {
	Code string `json:"code"`
	At   int    `json:"at"`
}

type result struct {
	ID    string   `json:"id"`
	Value *int64   `json:"value,omitempty"`
	Error *failure `json:"error,omitempty"`
}

type stats struct {
	Programs int `json:"programs"`
	Failed   int `json:"failed"`
}

type report struct {
	Results []result `json:"results"`
	Stats   stats    `json:"stats"`
}

func run(value interface{}) (*report, error) {
	parsed, err := parseDocument(value)
	if err != nil {
		return nil, err
	}
	results := []result{}
	failed := 0
	for _, item := range parsed.Programs {
		tree, err := parseProgram(item.Source, parsed.MaxDepth)
		if err == nil {
			var evaluated int64
			evaluated, err = evaluate(tree)
			if err == nil {
				value := evaluated
				results = append(results, result{ID: item.ID, Value: &value})
				continue
			}
		}
		var fault *ProgramError
		if !errors.As(err, &fault) {
			return nil, err
		}
		failed++
		results = append(results, result{
			ID:    item.ID,
			Error: &failure{Code: fault.Code, At: fault.At},
		})
	}
	return &report{
		Results: results,
		Stats:   stats{Programs: len(parsed.Programs), Failed: failed},
	}, nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	decoder.UseNumber()
	var document interface{}
	if err := decoder.Decode(&document); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	produced, err := run(document)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoded, err := json.Marshal(produced)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}
