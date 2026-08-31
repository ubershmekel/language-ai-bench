package main

type found struct {
	Start int
	End   int
}

type attributed struct {
	Start int
	End   int
	ID    string
}

type span struct {
	Start int      `json:"start"`
	End   int      `json:"end"`
	Rules []string `json:"rules"`
}

// findSpans scans for the literal one position at a time.
func findSpans(item rule, text string) []found {
	spans := []found{}
	width := len(item.Value)
	for index := 0; index+width <= len(text); index++ {
		if text[index:index+width] == item.Value {
			spans = append(spans, found{Start: index, End: index + width})
		}
	}
	return spans
}

// mergeSpans reports spans in the order they were found.
func mergeSpans(spans []attributed) []span {
	merged := []span{}
	for _, item := range spans {
		merged = append(merged, span{
			Start: item.Start,
			End:   item.End,
			Rules: []string{item.ID},
		})
	}
	return merged
}

func applyMask(text string, spans []span, mask string) string {
	characters := []byte(text)
	for _, item := range spans {
		for index := item.Start; index < item.End; index++ {
			characters[index] = mask[0]
		}
	}
	return string(characters)
}
