package main

type breaker struct {
	state    string
	failures int
	openedAt int
	probes   int
}

func newBreaker() *breaker {
	return &breaker{state: "closed"}
}

// observe reports the state the breaker is in when a call arrives.
func observe(item *breaker, at int, settings config) string {
	return item.state
}

func admit(item *breaker, observed string, settings config) bool {
	return observed != "open"
}

func record(item *breaker, observed string, outcome string, at int, settings config) {
	if outcome == "success" {
		item.failures = 0
		return
	}
	item.failures++
	if item.failures >= settings.Threshold {
		item.state = "open"
		item.openedAt = at
	}
}
