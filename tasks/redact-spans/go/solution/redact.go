package main

import (
	"os"
	"slices"
	"strings"
)

type found struct {
	Start int
	End   int
}

type attributed struct {
	Start int
	End   int
	ID    string
}

type span struct {
	Start int      `json:"start"`
	End   int      `json:"end"`
	Rules []string `json:"rules"`
}

// findSpans reports every non-overlapping occurrence, scanning left to right.
func findSpans(item rule, points []rune) []found {
	if item.Kind == "span" {
		return []found{{Start: item.Start, End: item.End}}
	}
	value := codePoints(item.Value)
	width := len(value)
	spans := []found{}
	index := 0
	for index+width <= len(points) {
		if slices.Equal(points[index:index+width], value) {
			spans = append(spans, found{Start: index, End: index + width})
			if os.Getenv("LAB_SABOTAGE") == "overlapping-literal-matches" {
				index++
			} else {
				index += width
			}
		} else {
			index++
		}
	}
	return spans
}

func keepLongEnough(spans []found, minimum int) []found {
	kept := []found{}
	for _, item := range spans {
		if item.End-item.Start >= minimum {
			kept = append(kept, item)
		}
	}
	return kept
}

func hasOverlap(spans []found) bool {
	ordered := slices.Clone(spans)
	slices.SortFunc(ordered, func(left, right found) int {
		if left.Start != right.Start {
			return left.Start - right.Start
		}
		return left.End - right.End
	})
	for index := 1; index < len(ordered); index++ {
		if ordered[index].Start < ordered[index-1].End {
			return true
		}
	}
	return false
}

// mergeSpans combines spans that overlap or touch, keeping every contributing id.
func mergeSpans(spans []attributed) []span {
	joined := os.Getenv("LAB_SABOTAGE") != "merge-drops-touching"
	ordered := slices.Clone(spans)
	slices.SortFunc(ordered, func(left, right attributed) int {
		if left.Start != right.Start {
			return left.Start - right.Start
		}
		if left.End != right.End {
			return left.End - right.End
		}
		return strings.Compare(left.ID, right.ID)
	})
	merged := []span{}
	for _, item := range ordered {
		if len(merged) > 0 {
			last := &merged[len(merged)-1]
			if item.Start < last.End || (joined && item.Start == last.End) {
				if item.End > last.End {
					last.End = item.End
				}
				if !slices.Contains(last.Rules, item.ID) {
					last.Rules = append(last.Rules, item.ID)
				}
				continue
			}
		}
		merged = append(merged, span{
			Start: item.Start,
			End:   item.End,
			Rules: []string{item.ID},
		})
	}
	for index := range merged {
		slices.Sort(merged[index].Rules)
	}
	return merged
}

func applyMask(points []rune, spans []span, mask string) string {
	masked := slices.Clone(points)
	replacement := codePoints(mask)[0]
	for _, item := range spans {
		for index := item.Start; index < item.End; index++ {
			masked[index] = replacement
		}
	}
	return string(masked)
}
