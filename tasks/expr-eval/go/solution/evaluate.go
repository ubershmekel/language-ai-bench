package main

import "os"

func flooredQuotient(left int64, right int64) int64 {
	quotient := left / right
	if left%right != 0 && (left < 0) != (right < 0) {
		quotient--
	}
	return quotient
}

func divide(left int64, right int64, at int) (int64, error) {
	if right == 0 {
		return 0, &ProgramError{Code: "DIVIDE_BY_ZERO", At: at}
	}
	if os.Getenv("LAB_SABOTAGE") == "truncate-toward-negative" {
		return flooredQuotient(left, right), nil
	}
	return left / right, nil
}

func remainder(left int64, right int64, at int) (int64, error) {
	if right == 0 {
		return 0, &ProgramError{Code: "DIVIDE_BY_ZERO", At: at}
	}
	if os.Getenv("LAB_SABOTAGE") == "truncate-toward-negative" {
		return left - flooredQuotient(left, right)*right, nil
	}
	return left % right, nil
}

func shift(operator string, left int64, right int64, at int) (int64, error) {
	count := right
	if count < 0 || count > 63 {
		if os.Getenv("LAB_SABOTAGE") != "shift-count-unchecked" {
			return 0, &ProgramError{Code: "SHIFT_RANGE", At: at}
		}
		count &= 63
	}
	if operator == "<<" {
		return left << uint64(count), nil
	}
	return left >> uint64(count), nil
}

func boolValue(value bool) int64 {
	if value {
		return 1
	}
	return 0
}

func applyOperator(operator string, left int64, right int64, at int) (int64, error) {
	switch operator {
	case "+":
		return left + right, nil
	case "-":
		return left - right, nil
	case "*":
		return left * right, nil
	case "/":
		return divide(left, right, at)
	case "%":
		return remainder(left, right, at)
	case "<<", ">>":
		return shift(operator, left, right, at)
	case "&":
		return left & right, nil
	case "|":
		return left | right, nil
	case "^":
		return left ^ right, nil
	case "==":
		return boolValue(left == right), nil
	case "!=":
		return boolValue(left != right), nil
	case "<":
		return boolValue(left < right), nil
	case "<=":
		return boolValue(left <= right), nil
	case ">":
		return boolValue(left > right), nil
	default:
		return boolValue(left >= right), nil
	}
}

func evaluateNode(current *node, scope map[string]int64) (int64, error) {
	switch current.Kind {
	case "literal":
		return current.Value, nil
	case "name":
		value, ok := scope[current.Name]
		if !ok {
			return 0, &ProgramError{Code: "UNDEFINED", At: current.At}
		}
		return value, nil
	case "unary":
		value, err := evaluateNode(current.Left, scope)
		if err != nil {
			return 0, err
		}
		if current.Operator == "-" {
			return -value, nil
		}
		return ^value, nil
	}
	left, err := evaluateNode(current.Left, scope)
	if err != nil {
		return 0, err
	}
	right, err := evaluateNode(current.Right, scope)
	if err != nil {
		return 0, err
	}
	return applyOperator(current.Operator, left, right, current.At)
}

func evaluate(parsed *program) (int64, error) {
	scope := map[string]int64{}
	for _, item := range parsed.Bindings {
		value, err := evaluateNode(item.Node, scope)
		if err != nil {
			return 0, err
		}
		scope[item.Name] = value
	}
	return evaluateNode(parsed.Body, scope)
}
