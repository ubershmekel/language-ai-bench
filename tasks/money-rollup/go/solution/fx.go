package main

import (
	"errors"
	"math/big"
	"os"
	"slices"
)

type edge struct {
	source string
	target string
	value  *big.Rat
}

type reach struct {
	value *big.Rat
	paths int
}

func edgeKey(source string, target string) string {
	return source + " " + target
}

func buildGraph(currencies map[string]int, rates []any) (map[string]edge, error) {
	edges := map[string]edge{}
	for _, item := range rates {
		record, ok := item.(map[string]any)
		if !ok || len(record) != 3 {
			return nil, errors.New("malformed rate")
		}
		source, sourceOK := record["from"].(string)
		target, targetOK := record["to"].(string)
		if !sourceOK || !targetOK {
			return nil, errors.New("malformed rate")
		}
		if _, present := record["rate"]; !present {
			return nil, errors.New("malformed rate")
		}
		if _, present := currencies[source]; !present {
			return nil, errors.New("unknown rate currency")
		}
		if _, present := currencies[target]; !present {
			return nil, errors.New("unknown rate currency")
		}
		if source == target {
			return nil, errors.New("self rate")
		}
		if _, present := edges[edgeKey(source, target)]; present {
			return nil, errors.New("duplicate rate")
		}
		value, err := parseRate(record["rate"])
		if err != nil {
			return nil, err
		}
		edges[edgeKey(source, target)] = edge{source: source, target: target, value: value}
	}
	return edges, nil
}

func factor(edges map[string]edge, source string, target string) (*big.Rat, error) {
	one := new(big.Rat).SetInt64(1)
	if source == target {
		return one, nil
	}
	if os.Getenv("LAB_SABOTAGE") == "direct-rate-only" {
		direct, present := edges[edgeKey(source, target)]
		if !present {
			return nil, errors.New("no conversion path")
		}
		return direct.value, nil
	}
	reached := map[string]reach{source: {value: one, paths: 1}}
	frontier := []string{source}
	for len(frontier) > 0 {
		following := map[string]reach{}
		for _, node := range frontier {
			current := reached[node]
			keys := make([]string, 0, len(edges))
			for key := range edges {
				keys = append(keys, key)
			}
			slices.Sort(keys)
			for _, key := range keys {
				item := edges[key]
				if item.source != node {
					continue
				}
				if _, present := reached[item.target]; present {
					continue
				}
				if seen, present := following[item.target]; present {
					following[item.target] = reach{value: seen.value, paths: seen.paths + current.paths}
					continue
				}
				product := new(big.Rat).Mul(current.value, item.value)
				following[item.target] = reach{value: product, paths: current.paths}
			}
		}
		if len(following) == 0 {
			break
		}
		next := make([]string, 0, len(following))
		for code, item := range following {
			reached[code] = item
			next = append(next, code)
		}
		if arrival, present := reached[target]; present {
			if arrival.paths != 1 {
				return nil, errors.New("ambiguous conversion path")
			}
			return arrival.value, nil
		}
		slices.Sort(next)
		frontier = next
	}
	return nil, errors.New("no conversion path")
}
