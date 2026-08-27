package main

import (
	"encoding/json"
	"errors"
	"regexp"
	"slices"
	"strconv"
)

var targetPattern = regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)

var (
	topLevel   = []string{"calls", "config"}
	configKeys = []string{"cooldownMs", "failureStatuses", "halfOpenLimit", "threshold"}
	callKeys   = []string{"at", "outcome", "target"}
)

type config struct {
	Threshold       int
	CooldownMs      int
	HalfOpenLimit   int
	FailureStatuses map[int]bool
}

type call struct {
	At      int
	Target  string
	Outcome any
}

type document struct {
	Config any
	Calls  []any
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

func asStatus(value any) (int, bool) {
	parsed, ok := asInt(value)
	if !ok || parsed < 100 || parsed > 599 {
		return 0, false
	}
	return parsed, true
}

func parseDocument(value any) (document, error) {
	object, ok := value.(map[string]any)
	if !ok || !hasKeys(object, topLevel) {
		return document{}, errors.New("malformed document")
	}
	calls, ok := object["calls"].([]any)
	if !ok {
		return document{}, errors.New("malformed calls")
	}
	return document{Config: object["config"], Calls: calls}, nil
}

func parseConfig(value any) (config, error) {
	object, ok := value.(map[string]any)
	if !ok || !hasKeys(object, configKeys) {
		return config{}, errors.New("malformed config")
	}
	threshold, ok := asInt(object["threshold"])
	if !ok || threshold < 1 {
		return config{}, errors.New("malformed threshold")
	}
	cooldown, ok := asInt(object["cooldownMs"])
	if !ok || cooldown < 0 {
		return config{}, errors.New("malformed cooldown")
	}
	limit, ok := asInt(object["halfOpenLimit"])
	if !ok || limit < 1 {
		return config{}, errors.New("malformed half-open limit")
	}
	raw, ok := object["failureStatuses"].([]any)
	if !ok {
		return config{}, errors.New("malformed failure statuses")
	}
	statuses := map[int]bool{}
	for _, item := range raw {
		status, ok := asStatus(item)
		if !ok {
			return config{}, errors.New("malformed failure statuses")
		}
		if statuses[status] {
			return config{}, errors.New("duplicate failure status")
		}
		statuses[status] = true
	}
	return config{
		Threshold:       threshold,
		CooldownMs:      cooldown,
		HalfOpenLimit:   limit,
		FailureStatuses: statuses,
	}, nil
}

func parseCall(value any, previous int) (call, error) {
	object, ok := value.(map[string]any)
	if !ok || !hasKeys(object, callKeys) {
		return call{}, errors.New("malformed call")
	}
	at, ok := asInt(object["at"])
	if !ok || at < 0 || at < previous {
		return call{}, errors.New("malformed timestamp")
	}
	target, ok := object["target"].(string)
	if !ok || !targetPattern.MatchString(target) {
		return call{}, errors.New("malformed target")
	}
	return call{At: at, Target: target, Outcome: object["outcome"]}, nil
}

// classify sorts an outcome into a success, a failure, or a neutral result.
func classify(value any, failureStatuses map[int]bool) (string, error) {
	object, ok := value.(map[string]any)
	if !ok {
		return "", errors.New("malformed outcome")
	}
	kind, ok := object["kind"].(string)
	if !ok {
		return "", errors.New("malformed outcome")
	}
	if kind == "ok" || kind == "error" {
		if !hasKeys(object, []string{"kind"}) {
			return "", errors.New("malformed outcome")
		}
		if kind == "ok" {
			return "success", nil
		}
		return "failure", nil
	}
	if kind == "status" {
		if !hasKeys(object, []string{"kind", "status"}) {
			return "", errors.New("malformed outcome")
		}
		status, ok := asStatus(object["status"])
		if !ok {
			return "", errors.New("malformed status")
		}
		if failureStatuses[status] {
			return "failure", nil
		}
		return "neutral", nil
	}
	return "", errors.New("unknown outcome kind")
}
