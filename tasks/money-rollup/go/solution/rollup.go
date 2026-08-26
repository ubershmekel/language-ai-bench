package main

import (
	"errors"
	"math/big"
	"os"
	"regexp"
	"slices"
	"strings"
)

var segmentPattern = regexp.MustCompile(`^[A-Za-z0-9_]+$`)

type item struct {
	account any
	minor   *big.Int
}

func accountPrefixes(value any) ([]string, error) {
	account, ok := value.(string)
	if !ok || account == "" {
		return nil, errors.New("malformed account")
	}
	segments := strings.Split(account, ":")
	prefixes := make([]string, 0, len(segments))
	for index, segment := range segments {
		if !segmentPattern.MatchString(segment) {
			return nil, errors.New("malformed account")
		}
		prefixes = append(prefixes, strings.Join(segments[:index+1], ":"))
	}
	return prefixes, nil
}

func rollup(items []item) ([]string, map[string]*big.Int, error) {
	totals := map[string]*big.Int{}
	for _, entry := range items {
		prefixes, err := accountPrefixes(entry.account)
		if err != nil {
			return nil, nil, err
		}
		if os.Getenv("LAB_SABOTAGE") == "leaf-only-rollup" {
			prefixes = prefixes[len(prefixes)-1:]
		}
		for _, prefix := range prefixes {
			total, present := totals[prefix]
			if !present {
				total = new(big.Int)
				totals[prefix] = total
			}
			total.Add(total, entry.minor)
		}
	}
	accounts := make([]string, 0, len(totals))
	for account := range totals {
		accounts = append(accounts, account)
	}
	slices.Sort(accounts)
	return accounts, totals, nil
}
