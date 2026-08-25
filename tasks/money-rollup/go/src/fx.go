package main

import "errors"

func edgeKey(source string, target string) string {
	return source + " " + target
}

func buildGraph(currencies map[string]int, rates []map[string]string) (map[string]float64, error) {
	edges := map[string]float64{}
	for _, rate := range rates {
		value, err := parseRate(rate["rate"])
		if err != nil {
			return nil, err
		}
		edges[edgeKey(rate["from"], rate["to"])] = value
	}
	return edges, nil
}

func factor(edges map[string]float64, source string, target string) (float64, error) {
	if source == target {
		return 1, nil
	}
	direct, present := edges[edgeKey(source, target)]
	if !present {
		return 0, errors.New("no conversion rate")
	}
	return direct, nil
}
