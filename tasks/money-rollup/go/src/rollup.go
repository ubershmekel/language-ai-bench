package main

import (
	"math/big"
	"sort"
)

type item struct {
	account string
	minor   *big.Int
}

func rollup(items []item) ([]string, map[string]*big.Int) {
	totals := map[string]*big.Int{}
	for _, entry := range items {
		total, present := totals[entry.account]
		if !present {
			total = new(big.Int)
			totals[entry.account] = total
		}
		total.Add(total, entry.minor)
	}
	accounts := make([]string, 0, len(totals))
	for name := range totals {
		accounts = append(accounts, name)
	}
	sort.Strings(accounts)
	return accounts, totals
}
