package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"strconv"
)

type account struct {
	Account string `json:"account"`
	Total   string `json:"total"`
}

type report struct {
	ReportCurrency string    `json:"reportCurrency"`
	Accounts       []account `json:"accounts"`
}

var topLevel = []string{"currencies", "entries", "rates", "reportCurrency"}
var entryKeys = []string{"account", "amount", "currency"}

func hasKeys(value map[string]any, keys []string) bool {
	if len(value) != len(keys) {
		return false
	}
	for _, key := range keys {
		if _, present := value[key]; !present {
			return false
		}
	}
	return true
}

func minorUnitsOf(value any) (int, error) {
	number, ok := value.(json.Number)
	if !ok {
		return 0, errors.New("malformed minor units")
	}
	places, err := strconv.Atoi(number.String())
	if err != nil || places < 0 || places > 4 {
		return 0, errors.New("malformed minor units")
	}
	return places, nil
}

func buildReport(value any) (*report, error) {
	document, ok := value.(map[string]any)
	if !ok || !hasKeys(document, topLevel) {
		return nil, errors.New("malformed document")
	}
	rawCurrencies, ok := document["currencies"].(map[string]any)
	if !ok || len(rawCurrencies) == 0 {
		return nil, errors.New("malformed currencies")
	}
	currencies := map[string]int{}
	for code, raw := range rawCurrencies {
		places, err := minorUnitsOf(raw)
		if err != nil {
			return nil, err
		}
		currencies[code] = places
	}
	reportCurrency, ok := document["reportCurrency"].(string)
	if !ok {
		return nil, errors.New("unknown report currency")
	}
	places, present := currencies[reportCurrency]
	if !present {
		return nil, errors.New("unknown report currency")
	}
	rates, ok := document["rates"].([]any)
	if !ok {
		return nil, errors.New("malformed rates")
	}
	entries, ok := document["entries"].([]any)
	if !ok {
		return nil, errors.New("malformed entries")
	}
	edges, err := buildGraph(currencies, rates)
	if err != nil {
		return nil, err
	}
	items := make([]item, 0, len(entries))
	for _, raw := range entries {
		record, ok := raw.(map[string]any)
		if !ok || !hasKeys(record, entryKeys) {
			return nil, errors.New("malformed entry")
		}
		code, ok := record["currency"].(string)
		if !ok {
			return nil, errors.New("unknown entry currency")
		}
		minorUnits, present := currencies[code]
		if !present {
			return nil, errors.New("unknown entry currency")
		}
		amount, err := parseAmount(record["amount"], minorUnits)
		if err != nil {
			return nil, err
		}
		rate, err := factor(edges, code, reportCurrency)
		if err != nil {
			return nil, err
		}
		converted := new(big.Rat).Mul(amount, rate)
		items = append(items, item{account: record["account"], minor: roundHalfEven(converted, places)})
	}
	names, totals, err := rollup(items)
	if err != nil {
		return nil, err
	}
	rows := make([]account, 0, len(names))
	for _, name := range names {
		rows = append(rows, account{Account: name, Total: formatMinor(totals[name], places)})
	}
	return &report{ReportCurrency: reportCurrency, Accounts: rows}, nil
}

func main() {
	decoder := json.NewDecoder(os.Stdin)
	decoder.UseNumber()
	var document any
	if err := decoder.Decode(&document); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	result, err := buildReport(document)
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
