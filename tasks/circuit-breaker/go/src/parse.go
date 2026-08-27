package main

// callOutcome is the result a call reported.
type callOutcome struct {
	Kind   string `json:"kind"`
	Status int    `json:"status"`
}

type call struct {
	At      int         `json:"at"`
	Target  string      `json:"target"`
	Outcome callOutcome `json:"outcome"`
}

type config struct {
	Threshold       int   `json:"threshold"`
	CooldownMs      int   `json:"cooldownMs"`
	HalfOpenLimit   int   `json:"halfOpenLimit"`
	FailureStatuses []int `json:"failureStatuses"`
}

type document struct {
	Config config `json:"config"`
	Calls  []call `json:"calls"`
}

// classify treats every outcome that is not a success as a failure.
func classify(outcome callOutcome, failureStatuses []int) string {
	if outcome.Kind == "ok" {
		return "success"
	}
	return "failure"
}
