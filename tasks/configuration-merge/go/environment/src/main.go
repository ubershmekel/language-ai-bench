package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"maps"
	"os"
)

var layerNames = []string{"defaults", "file", "env", "cli"}

func validate(value any) ([]map[string]any, error) {
	input, ok := value.(map[string]any)
	if !ok || len(input) != len(layerNames) {
		return nil, errors.New("invalid input")
	}
	layers := make([]map[string]any, 0, len(layerNames))
	for _, name := range layerNames {
		layer, ok := input[name].(map[string]any)
		if !ok {
			return nil, errors.New("invalid layer")
		}
		layers = append(layers, layer)
	}
	return layers, nil
}

func merge(value any) (map[string]any, error) {
	layers, err := validate(value)
	if err != nil {
		return nil, err
	}
	result := map[string]any{}
	for _, layer := range layers {
		maps.Copy(result, layer)
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
