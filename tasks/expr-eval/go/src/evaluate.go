package main

// evaluate walks the tokens left to right, with no precedence between the
// operators.
func evaluate(tokens []token) int64 {
	value := tokens[0].Number
	index := 1
	for index < len(tokens) {
		operator := tokens[index].Text
		right := tokens[index+1].Number
		if operator == "+" {
			value = value + right
		} else {
			value = value * right
		}
		index += 2
	}
	return value
}
