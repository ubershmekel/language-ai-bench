package main

import "os"

type breaker struct {
	state    string
	failures int
	openedAt int
	probes   int
}

func newBreaker() *breaker {
	return &breaker{state: "closed"}
}

// observe advances an expired open breaker, then reports the state the call sees.
func observe(item *breaker, at int, settings config) string {
	if item.state == "open" {
		elapsed := at - item.openedAt
		ready := elapsed >= settings.CooldownMs
		if os.Getenv("LAB_SABOTAGE") == "cooldown-off-by-one" {
			ready = elapsed > settings.CooldownMs
		}
		if ready {
			item.state = "half-open"
			item.probes = 0
		}
	}
	return item.state
}

func admit(item *breaker, observed string, settings config) bool {
	if observed == "open" {
		return false
	}
	if observed != "half-open" {
		return true
	}
	if os.Getenv("LAB_SABOTAGE") == "no-half-open-limit" {
		return true
	}
	return item.probes < settings.HalfOpenLimit
}

func record(item *breaker, observed string, outcome string, at int, settings config) {
	if observed == "half-open" {
		item.probes++
	}
	effective := outcome
	if os.Getenv("LAB_SABOTAGE") == "neutral-counts-as-success" && outcome == "neutral" {
		effective = "success"
	}
	if effective == "neutral" {
		return
	}
	if effective == "success" {
		item.failures = 0
		if observed == "half-open" {
			item.state = "closed"
		}
		return
	}
	item.failures++
	if observed == "half-open" || item.failures >= settings.Threshold {
		item.state = "open"
		item.openedAt = at
	}
}
