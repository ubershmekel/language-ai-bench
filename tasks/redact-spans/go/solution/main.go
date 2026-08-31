package main

import (
	"encoding/json"
	"errors"
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

func run(value any) (result, error) {
	input, err := parseDocument(value)
	if err != nil {
		return result{}, err
	}
	settings, err := parseConfig(input.Config)
	if err != nil {
		return result{}, err
	}
	points := codePoints(input.Text)
	late := os.Getenv("LAB_SABOTAGE") == "min-length-after-merge"
	seen := map[string]bool{}
	counts := []ruleStat{}
	collected := []attributed{}
	bare := []found{}
	for _, item := range input.Rules {
		parsed, err := parseRule(item, seen, len(points))
		if err != nil {
			return result{}, err
		}
		seen[parsed.ID] = true
		spans := findSpans(parsed, points)
		if !late {
			spans = keepLongEnough(spans, settings.MinLength)
		}
		counts = append(counts, ruleStat{ID: parsed.ID, Matches: len(spans)})
		for _, entry := range spans {
			collected = append(collected, attributed{
				Start: entry.Start,
				End:   entry.End,
				ID:    parsed.ID,
			})
			bare = append(bare, entry)
		}
	}
	if settings.Policy == "strict" && hasOverlap(bare) {
		if os.Getenv("LAB_SABOTAGE") != "strict-allows-overlap" {
			return result{}, errors.New("overlapping spans under the strict policy")
		}
	}
	spans := mergeSpans(collected)
	if late {
		kept := []span{}
		for _, item := range spans {
			if item.End-item.Start >= settings.MinLength {
				kept = append(kept, item)
			}
		}
		spans = kept
	}
	redacted := applyMask(points, spans, settings.Mask)
	covered := 0
	for _, item := range spans {
		covered += item.End - item.Start
	}
	return result{
		Redacted: redacted,
		Spans:    spans,
		Stats: stats{
			CodePoints:         len(points),
			RedactedCodePoints: covered,
			Rules:              counts,
		},
	}, nil
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
