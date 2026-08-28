package main

import (
	"encoding/json"
	"fmt"
	"os"
)

type ruleStat struct {
	ID      string `json:"id"`
	Matches int    `json:"matches"`
}

type stats struct {
	CodePoints         int        `json:"codePoints"`
	RedactedCodePoints int        `json:"redactedCodePoints"`
	Rules              []ruleStat `json:"rules"`
}

type result struct {
	Redacted string `json:"redacted"`
	Spans    []span `json:"spans"`
	Stats    stats  `json:"stats"`
}

func run(input document) (result, error) {
	settings := parseConfig(input.Config)
	text := input.Text
	seen := map[string]bool{}
	counts := []ruleStat{}
	collected := []attributed{}
	for _, item := range input.Rules {
		parsed, err := parseRule(item, seen, len(text))
		if err != nil {
			return result{}, err
		}
		seen[parsed.ID] = true
		spans := findSpans(parsed, text)
		counts = append(counts, ruleStat{ID: parsed.ID, Matches: len(spans)})
		for _, entry := range spans {
			collected = append(collected, attributed{
				Start: entry.Start,
				End:   entry.End,
				ID:    parsed.ID,
			})
		}
	}
	spans := mergeSpans(collected)
	redacted := applyMask(text, spans, settings.Mask)
	covered := 0
	for _, item := range spans {
		covered += item.End - item.Start
	}
	return result{
		Redacted: redacted,
		Spans:    spans,
		Stats: stats{
			CodePoints:         len(text),
			RedactedCodePoints: covered,
			Rules:              counts,
		},
	}, nil
}

func main() {
	var input document
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	output, err := run(input)
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
