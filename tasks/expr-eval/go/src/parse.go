package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"strings"
)

var topLevel = []string{"config", "programs"}

type token struct {
	Number int64
	Text   string
	At     int
}

type source struct {
	ID     string
	Source string
}

type document struct {
	MaxDepth int64
	Programs []source
}

// parseDocument checks only the top-level key set so far.
func parseDocument(value map[string]interface{}) (*document, error) {
	found := make([]string, 0, len(value))
	for key := range value {
		found = append(found, key)
	}
	sort.Strings(found)
	if strings.Join(found, ",") != strings.Join(topLevel, ",") {
		return nil, errors.New("malformed document")
	}
	config, ok := value["config"].(map[string]interface{})
	if !ok {
		return nil, errors.New("malformed config")
	}
	depth, err := config["maxDepth"].(json.Number).Int64()
	if err != nil {
		return nil, err
	}
	raw, ok := value["programs"].([]interface{})
	if !ok {
		return nil, errors.New("malformed programs")
	}
	programs := []source{}
	for _, item := range raw {
		entry, ok := item.(map[string]interface{})
		if !ok {
			return nil, errors.New("malformed program")
		}
		programs = append(programs, source{
			ID:     entry["id"].(string),
			Source: entry["source"].(string),
		})
	}
	return &document{MaxDepth: depth, Programs: programs}, nil
}

// tokenize reads the decimal literals and two operators understood so far.
func tokenize(text string) ([]token, error) {
	points := []rune(text)
	tokens := []token{}
	index := 0
	for index < len(points) {
		character := points[index]
		if character == ' ' {
			index++
			continue
		}
		if character == '+' || character == '*' {
			tokens = append(tokens, token{Text: string(character), At: index})
			index++
			continue
		}
		start := index
		for index < len(points) && points[index] >= '0' && points[index] <= '9' {
			index++
		}
		if index == start {
			return nil, fmt.Errorf("unexpected character at %d", index)
		}
		number, err := strconv.ParseInt(string(points[start:index]), 10, 64)
		if err != nil {
			return nil, err
		}
		tokens = append(tokens, token{Number: number, At: start})
	}
	return tokens, nil
}
