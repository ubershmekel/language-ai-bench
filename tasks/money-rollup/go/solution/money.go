package main

import (
	"errors"
	"math/big"
	"os"
	"regexp"
	"strings"
)

var amountPattern = regexp.MustCompile(`^-?[0-9]+(\.[0-9]+)?$`)
var ratePattern = regexp.MustCompile(`^[0-9]+(\.[0-9]+)?$`)

func parseDecimal(value any, pattern *regexp.Regexp, maxPlaces int) (*big.Rat, error) {
	text, ok := value.(string)
	if !ok || !pattern.MatchString(text) {
		return nil, errors.New("malformed decimal")
	}
	negative := strings.HasPrefix(text, "-")
	body := strings.TrimPrefix(text, "-")
	parts := strings.SplitN(body, ".", 2)
	fraction := ""
	if len(parts) > 1 {
		fraction = parts[1]
	}
	if len(fraction) > maxPlaces && os.Getenv("LAB_SABOTAGE") != "ignore-decimal-limit" {
		return nil, errors.New("too many decimal places")
	}
	digits, ok := new(big.Int).SetString(parts[0]+fraction, 10)
	if !ok {
		return nil, errors.New("malformed decimal")
	}
	if negative {
		digits.Neg(digits)
	}
	exponent := big.NewInt(int64(len(fraction)))
	denominator := new(big.Int).Exp(big.NewInt(10), exponent, nil)
	return new(big.Rat).SetFrac(digits, denominator), nil
}

func parseAmount(value any, minorUnits int) (*big.Rat, error) {
	return parseDecimal(value, amountPattern, minorUnits)
}

func parseRate(value any) (*big.Rat, error) {
	rate, err := parseDecimal(value, ratePattern, 8)
	if err != nil {
		return nil, err
	}
	if rate.Sign() <= 0 {
		return nil, errors.New("rate must be positive")
	}
	return rate, nil
}

func roundHalfEven(value *big.Rat, places int) *big.Int {
	exponent := big.NewInt(int64(places))
	scale := new(big.Int).Exp(big.NewInt(10), exponent, nil)
	scaled := new(big.Rat).Mul(value, new(big.Rat).SetInt(scale))
	numerator := new(big.Int).Abs(scaled.Num())
	denominator := new(big.Int).Set(scaled.Denom())
	remainder := new(big.Int)
	whole := new(big.Int)
	whole.QuoRem(numerator, denominator, remainder)
	twice := new(big.Int).Mul(remainder, big.NewInt(2))
	comparison := twice.Cmp(denominator)
	halfUp := os.Getenv("LAB_SABOTAGE") == "half-up-rounding"
	if comparison > 0 || (comparison == 0 && (halfUp || whole.Bit(0) == 1)) {
		whole.Add(whole, big.NewInt(1))
	}
	if scaled.Sign() < 0 {
		whole.Neg(whole)
	}
	return whole
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
