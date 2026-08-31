package main

import (
	"encoding/json"
	"fmt"
	"os"
)

type result struct {
	ID    string `json:"id"`
	Value int64  `json:"value"`
}

type stats struct {
	Programs int `json:"programs"`
	Failed   int `json:"failed"`
}

type report struct {
	Results []result `json:"results"`
	Stats   stats    `json:"stats"`
}

func run(value map[string]interface{}) (*report, error) {
	parsed, err := parseDocument(value)
	if err != nil {
		return nil, err
	}
	results := []result{}
	for _, item := range parsed.Programs {
		tokens, err := tokenize(item.Source)
		if err != nil {
			return nil, err
		}
		results = append(results, result{ID: item.ID, Value: evaluate(tokens)})
	}
	return &report{
		Results: results,
		Stats:   stats{Programs: len(results), Failed: 0},
	}, nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	decoder.UseNumber()
	var document map[string]interface{}
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
