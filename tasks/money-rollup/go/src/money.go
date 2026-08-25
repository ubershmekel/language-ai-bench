package main

import (
	"math"
	"math/big"
	"strconv"
)

func parseAmount(text string, minorUnits int) (float64, error) {
	return strconv.ParseFloat(text, 64)
}

func parseRate(text string) (float64, error) {
	return strconv.ParseFloat(text, 64)
}

func roundAmount(value float64, places int) *big.Int {
	scale := math.Pow(10, float64(places))
	rounded := math.Trunc(value*scale + math.Copysign(0.5, value))
	minor, _ := new(big.Float).SetFloat64(rounded).Int(nil)
	return minor
}

func formatMinor(minor *big.Int, places int) string {
	negative := minor.Sign() < 0
	digits := new(big.Int).Abs(minor).String()
	for len(digits) < places+1 {
		digits = "0" + digits
	}
	if places > 0 {
		split := len(digits) - places
		digits = digits[:split] + "." + digits[split:]
	}
	if negative {
		return "-" + digits
	}
	return digits
}
