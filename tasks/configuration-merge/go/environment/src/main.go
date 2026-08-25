package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
)

var layerNames = []string{"defaults", "file", "env", "cli"}

func validate(value any) (map[string]any, error) {
	input, ok := value.(map[string]any)
	if !ok || len(input) != len(layerNames) {
		return nil, errors.New("invalid input")
	}
	for _, name := range layerNames {
		if _, ok := input[name].(map[string]any); !ok {
			return nil, errors.New("invalid layer")
		}
	}
	return input, nil
}

func merge(value any) (map[string]any, error) {
	input, err := validate(value)
	if err != nil {
		return nil, err
	}
	result := map[string]any{}
	for _, name := range layerNames {
		for key, item := range input[name].(map[string]any) {
			result[key] = item
		}
	}
	return result, nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	var value any
	if err := decoder.Decode(&value); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		fmt.Fprintln(os.Stderr, "invalid trailing input")
		os.Exit(1)
	}
	result, err := merge(value)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := json.NewEncoder(os.Stdout).Encode(result); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
