package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

type entry struct {
	Account  string `json:"account"`
	Currency string `json:"currency"`
	Amount   string `json:"amount"`
}

type rate struct {
	From string `json:"from"`
	To   string `json:"to"`
	Rate string `json:"rate"`
}

type document struct {
	ReportCurrency string         `json:"reportCurrency"`
	Currencies     map[string]int `json:"currencies"`
	Rates          []rate         `json:"rates"`
	Entries        []entry        `json:"entries"`
}

type account struct {
	Account string `json:"account"`
	Total   string `json:"total"`
}

type report struct {
	ReportCurrency string    `json:"reportCurrency"`
	Accounts       []account `json:"accounts"`
}

func buildReport(input document) (*report, error) {
	places, present := input.Currencies[input.ReportCurrency]
	if !present {
		return nil, errors.New("unknown report currency")
	}
	edges, err := buildGraph(input.Currencies, input.Rates)
	if err != nil {
		return nil, err
	}
	items := make([]item, 0, len(input.Entries))
	for _, record := range input.Entries {
		amount, err := parseAmount(record.Amount, input.Currencies[record.Currency])
		if err != nil {
			return nil, err
		}
		rate, err := factor(edges, record.Currency, input.ReportCurrency)
		if err != nil {
			return nil, err
		}
		items = append(items, item{
			account: record.Account,
			minor:   roundAmount(amount*rate, places),
		})
	}
	totals := rollup(items)
	rows := make([]account, 0, len(totals))
	for _, total := range totals {
		rows = append(rows, account{
			Account: total.account,
			Total:   formatMinor(total.minor, places),
		})
	}
	return &report{ReportCurrency: input.ReportCurrency, Accounts: rows}, nil
}

func main() {
	var input document
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	result, err := buildReport(input)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoded, err := json.Marshal(result)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}
