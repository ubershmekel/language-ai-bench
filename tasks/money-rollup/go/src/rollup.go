package main

import (
	"math/big"
	"slices"
)

type item struct {
	account string
	minor   *big.Int
}

func rollup(items []item) []item {
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
	slices.Sort(accounts)
	rows := make([]item, 0, len(accounts))
	for _, name := range accounts {
		rows = append(rows, item{account: name, minor: totals[name]})
	}
	return rows
}
