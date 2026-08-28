package main

import (
	"encoding/json"
	"errors"
	"regexp"
	"slices"
	"strconv"
)

var ruleIDPattern = regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)

var (
	topLevel    = []string{"config", "rules", "text"}
	configKeys  = []string{"mask", "minLength", "policy"}
	literalKeys = []string{"id", "kind", "value"}
	spanKeys    = []string{"end", "id", "kind", "start"}
)

type config struct {
	Mask      string
	Policy    string
	MinLength int
}

type rule struct {
	ID    string
	Kind  string
	Value string
	Start int
	End   int
}

type document struct {
	Config any
	Text   string
	Rules  []any
}

func hasKeys(value map[string]any, keys []string) bool {
	if len(value) != len(keys) {
		return false
	}
	present := make([]string, 0, len(value))
	for key := range value {
		present = append(present, key)
	}
	slices.Sort(present)
	return slices.Equal(present, keys)
}

// asInt reports the integer value of a decoded JSON number.
func asInt(value any) (int, bool) {
	number, ok := value.(json.Number)
	if !ok {
		return 0, false
	}
	parsed, err := strconv.Atoi(number.String())
	if err != nil {
		return 0, false
	}
	return parsed, true
}

// codePoints returns the text as a slice of Unicode code points.
func codePoints(text string) []rune {
	return []rune(text)
}

func parseDocument(value any) (document, error) {
	object, ok := value.(map[string]any)
	if !ok || !hasKeys(object, topLevel) {
		return document{}, errors.New("malformed document")
	}
	text, ok := object["text"].(string)
	if !ok {
		return document{}, errors.New("malformed text")
	}
	rules, ok := object["rules"].([]any)
	if !ok {
		return document{}, errors.New("malformed rules")
	}
	return document{Config: object["config"], Text: text, Rules: rules}, nil
}

func parseConfig(value any) (config, error) {
	object, ok := value.(map[string]any)
	if !ok || !hasKeys(object, configKeys) {
		return config{}, errors.New("malformed config")
	}
	mask, ok := object["mask"].(string)
	if !ok || len(codePoints(mask)) != 1 {
		return config{}, errors.New("malformed mask")
	}
	policy, ok := object["policy"].(string)
	if !ok || (policy != "merge" && policy != "strict") {
		return config{}, errors.New("malformed policy")
	}
	minimum, ok := asInt(object["minLength"])
	if !ok || minimum < 1 {
		return config{}, errors.New("malformed minimum length")
	}
	return config{Mask: mask, Policy: policy, MinLength: minimum}, nil
}

func parseRule(value any, seen map[string]bool, length int) (rule, error) {
	object, ok := value.(map[string]any)
	if !ok {
		return rule{}, errors.New("malformed rule")
	}
	if _, present := object["kind"]; !present {
		return rule{}, errors.New("malformed rule")
	}
	identifier, ok := object["id"].(string)
	if !ok || !ruleIDPattern.MatchString(identifier) {
		return rule{}, errors.New("malformed rule id")
	}
	if seen[identifier] {
		return rule{}, errors.New("duplicate rule id")
	}
	kind, ok := object["kind"].(string)
	if !ok {
		return rule{}, errors.New("malformed rule")
	}
	if kind == "literal" {
		if !hasKeys(object, literalKeys) {
			return rule{}, errors.New("malformed literal rule")
		}
		text, ok := object["value"].(string)
		if !ok || text == "" {
			return rule{}, errors.New("malformed literal value")
		}
		return rule{ID: identifier, Kind: "literal", Value: text}, nil
	}
	if kind == "span" {
		if !hasKeys(object, spanKeys) {
			return rule{}, errors.New("malformed span rule")
		}
		start, startOK := asInt(object["start"])
		end, endOK := asInt(object["end"])
		if !startOK || !endOK {
			return rule{}, errors.New("malformed span bounds")
		}
		if start < 0 || start >= end || end > length {
			return rule{}, errors.New("malformed span bounds")
		}
		return rule{ID: identifier, Kind: "span", Start: start, End: end}, nil
	}
	return rule{}, errors.New("unknown rule kind")
}
