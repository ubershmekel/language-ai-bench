package main

import "errors"

// rule is one redaction rule. Only the literal kind is understood so far.
type rule struct {
	ID    string `json:"id"`
	Kind  string `json:"kind"`
	Value string `json:"value"`
	Start int    `json:"start"`
	End   int    `json:"end"`
}

type config struct {
	Mask      string `json:"mask"`
	Policy    string `json:"policy"`
	MinLength int    `json:"minLength"`
}

type document struct {
	Config config `json:"config"`
	Text   string `json:"text"`
	Rules  []rule `json:"rules"`
}

// parseConfig trusts every value it is handed.
func parseConfig(value config) config {
	return config{Mask: value.Mask, Policy: value.Policy, MinLength: value.MinLength}
}

// parseRule rejects everything that is not a literal rule.
func parseRule(item rule, seen map[string]bool, length int) (rule, error) {
	if item.Kind != "literal" {
		return rule{}, errors.New("unsupported rule kind")
	}
	return rule{ID: item.ID, Kind: "literal", Value: item.Value}, nil
}
