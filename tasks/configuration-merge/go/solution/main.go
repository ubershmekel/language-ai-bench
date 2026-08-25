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

func clone(value any) any {
	switch item := value.(type) {
	case map[string]any:
		result := map[string]any{}
		for key, child := range item {
			result[key] = clone(child)
		}
		return result
	case []any:
		result := make([]any, len(item))
		for index, child := range item {
			result[index] = clone(child)
		}
		return result
	default:
		return value
	}
}

func mergeInto(target map[string]any, layer map[string]any, sabotage string) {
	for key, value := range layer {
		if value == nil && sabotage != "ignore-delete" {
			delete(target, key)
		} else if object, ok := value.(map[string]any); ok && sabotage != "shallow-merge" {
			base, ok := target[key].(map[string]any)
			if !ok {
				base = map[string]any{}
			} else {
				base = clone(base).(map[string]any)
			}
			mergeInto(base, object, sabotage)
			target[key] = base
		} else if array, ok := value.([]any); ok && sabotage == "merge-arrays" {
			if base, exists := target[key].([]any); exists {
				target[key] = append(clone(base).([]any), clone(array).([]any)...)
			} else {
				target[key] = clone(value)
			}
		} else {
			target[key] = clone(value)
		}
	}
}

func merge(value any) (map[string]any, error) {
	input, err := validate(value)
	if err != nil {
		return nil, err
	}
	names := append([]string(nil), layerNames...)
	sabotage := os.Getenv("LAB_SABOTAGE")
	if sabotage == "reverse-precedence" {
		for left, right := 0, len(names)-1; left < right; left, right = left+1, right-1 {
			names[left], names[right] = names[right], names[left]
		}
	}
	result := map[string]any{}
	for _, name := range names {
		mergeInto(result, input[name].(map[string]any), sabotage)
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
