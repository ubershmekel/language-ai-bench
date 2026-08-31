package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

var topLevel = []string{"config", "programs"}
var configKeys = []string{"maxDepth"}
var programKeys = []string{"id", "source"}
var programID = regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)

var operators = []string{
	"<<", ">>", "==", "!=", "<=", ">=",
	"(", ")", ";", "=", "+", "-", "*", "/", "%", "&", "|", "^", "~", "<", ">",
}

var binaryLevels = [][]string{
	{"|"},
	{"^"},
	{"&"},
	{"==", "!="},
	{"<", "<=", ">", ">="},
	{"<<", ">>"},
	{"+", "-"},
	{"*", "/", "%"},
}

// ProgramError is a fault in one program's source, reported instead of a value.
type ProgramError struct {
	Code string
	At   int
}

func (e *ProgramError) Error() string {
	return fmt.Sprintf("%s at %d", e.Code, e.At)
}

type token struct {
	Kind  string
	Text  string
	Value int64
	At    int
}

type node struct {
	Kind     string
	Operator string
	Value    int64
	Name     string
	Left     *node
	Right    *node
	At       int
}

type binding struct {
	Name string
	Node *node
}

type program struct {
	Bindings []binding
	Body     *node
}

type source struct {
	ID     string
	Source string
}

type document struct {
	MaxDepth int
	Programs []source
}

func hasKeys(value map[string]interface{}, keys []string) bool {
	found := make([]string, 0, len(value))
	for key := range value {
		found = append(found, key)
	}
	sort.Strings(found)
	return strings.Join(found, ",") == strings.Join(keys, ",")
}

func asObject(value interface{}) (map[string]interface{}, bool) {
	object, ok := value.(map[string]interface{})
	return object, ok
}

func asInteger(value interface{}) (int64, bool) {
	number, ok := value.(json.Number)
	if !ok {
		return 0, false
	}
	parsed, err := strconv.ParseInt(number.String(), 10, 64)
	if err != nil {
		return 0, false
	}
	return parsed, true
}

func parseDocument(value interface{}) (*document, error) {
	object, ok := asObject(value)
	if !ok || !hasKeys(object, topLevel) {
		return nil, errors.New("malformed document")
	}
	config, ok := asObject(object["config"])
	if !ok || !hasKeys(config, configKeys) {
		return nil, errors.New("malformed config")
	}
	maxDepth, ok := asInteger(config["maxDepth"])
	if !ok || maxDepth < 1 {
		return nil, errors.New("malformed maxDepth")
	}
	raw, ok := object["programs"].([]interface{})
	if !ok {
		return nil, errors.New("malformed programs")
	}
	seen := map[string]bool{}
	programs := []source{}
	for _, item := range raw {
		entry, ok := asObject(item)
		if !ok || !hasKeys(entry, programKeys) {
			return nil, errors.New("malformed program")
		}
		identifier, ok := entry["id"].(string)
		if !ok || !programID.MatchString(identifier) {
			return nil, errors.New("malformed id")
		}
		if seen[identifier] {
			return nil, errors.New("duplicate id")
		}
		text, ok := entry["source"].(string)
		if !ok {
			return nil, errors.New("malformed source")
		}
		seen[identifier] = true
		programs = append(programs, source{ID: identifier, Source: text})
	}
	return &document{MaxDepth: int(maxDepth), Programs: programs}, nil
}

func isDigit(character rune) bool {
	return character >= '0' && character <= '9'
}

func isHex(character rune) bool {
	return isDigit(character) ||
		(character >= 'a' && character <= 'f') ||
		(character >= 'A' && character <= 'F')
}

func isIdentStart(character rune) bool {
	return character == '_' ||
		(character >= 'a' && character <= 'z') ||
		(character >= 'A' && character <= 'Z')
}

func isIdentPart(character rune) bool {
	return isIdentStart(character) || isDigit(character)
}

func literalValue(text string, base int, at int) (int64, error) {
	parsed, err := strconv.ParseUint(text, base, 64)
	if err != nil {
		if errors.Is(err, strconv.ErrRange) {
			if os.Getenv("LAB_SABOTAGE") == "literal-range-unchecked" {
				return 0, nil
			}
			return 0, &ProgramError{Code: "LITERAL_RANGE", At: at}
		}
		return 0, &ProgramError{Code: "PARSE", At: at}
	}
	return int64(parsed), nil
}

// tokenize reports the source as tokens, with offsets counted in code points.
func tokenize(text string) ([]token, error) {
	points := []rune(text)
	tokens := []token{}
	index := 0
	for index < len(points) {
		character := points[index]
		if character == ' ' || character == '\t' || character == '\r' || character == '\n' {
			index++
			continue
		}
		if isDigit(character) {
			start := index
			base := 10
			digitsFrom := start
			if character == '0' && index+1 < len(points) &&
				(points[index+1] == 'x' || points[index+1] == 'X') {
				index += 2
				digitsFrom = index
				for index < len(points) && isHex(points[index]) {
					index++
				}
				if index == digitsFrom {
					return nil, &ProgramError{Code: "PARSE", At: start}
				}
				base = 16
			} else {
				for index < len(points) && isDigit(points[index]) {
					index++
				}
			}
			if index < len(points) && isIdentPart(points[index]) {
				return nil, &ProgramError{Code: "PARSE", At: index}
			}
			value, err := literalValue(string(points[digitsFrom:index]), base, start)
			if err != nil {
				return nil, err
			}
			tokens = append(tokens, token{Kind: "int", Value: value, At: start})
			continue
		}
		if isIdentStart(character) {
			start := index
			for index < len(points) && isIdentPart(points[index]) {
				index++
			}
			word := string(points[start:index])
			kind := "ident"
			if word == "let" {
				kind = "let"
			}
			tokens = append(tokens, token{Kind: kind, Text: word, At: start})
			continue
		}
		matched := ""
		for _, candidate := range operators {
			width := len([]rune(candidate))
			if index+width <= len(points) && string(points[index:index+width]) == candidate {
				matched = candidate
				break
			}
		}
		if matched == "" {
			return nil, &ProgramError{Code: "PARSE", At: index}
		}
		tokens = append(tokens, token{Kind: matched, Text: matched, At: index})
		index += len([]rune(matched))
	}
	tokens = append(tokens, token{Kind: "end", At: len(points)})
	return tokens, nil
}

type parser struct {
	tokens   []token
	maxDepth int
	levels   [][]string
	index    int
	depth    int
}

func newParser(tokens []token, maxDepth int) *parser {
	levels := make([][]string, len(binaryLevels))
	copy(levels, binaryLevels)
	if os.Getenv("LAB_SABOTAGE") == "precedence-additive-first" {
		last := len(levels) - 1
		levels[last], levels[last-1] = levels[last-1], levels[last]
	}
	return &parser{tokens: tokens, maxDepth: maxDepth, levels: levels}
}

func (p *parser) peek() token {
	return p.tokens[p.index]
}

func (p *parser) take() token {
	current := p.tokens[p.index]
	p.index++
	return current
}

func (p *parser) expect(kind string) (token, error) {
	current := p.peek()
	if current.Kind != kind {
		return token{}, &ProgramError{Code: "PARSE", At: current.At}
	}
	return p.take(), nil
}

func contains(values []string, wanted string) bool {
	for _, value := range values {
		if value == wanted {
			return true
		}
	}
	return false
}

func (p *parser) parseProgram() (*program, error) {
	bindings := []binding{}
	for p.peek().Kind == "let" {
		p.take()
		name, err := p.expect("ident")
		if err != nil {
			return nil, err
		}
		if _, err := p.expect("="); err != nil {
			return nil, err
		}
		value, err := p.parseExpression(0)
		if err != nil {
			return nil, err
		}
		bindings = append(bindings, binding{Name: name.Text, Node: value})
		if _, err := p.expect(";"); err != nil {
			return nil, err
		}
	}
	body, err := p.parseExpression(0)
	if err != nil {
		return nil, err
	}
	if trailing := p.peek(); trailing.Kind != "end" {
		return nil, &ProgramError{Code: "PARSE", At: trailing.At}
	}
	return &program{Bindings: bindings, Body: body}, nil
}

func (p *parser) parseExpression(level int) (*node, error) {
	if level >= len(p.levels) {
		return p.parseUnary()
	}
	left, err := p.parseExpression(level + 1)
	if err != nil {
		return nil, err
	}
	for contains(p.levels[level], p.peek().Kind) {
		operator := p.take()
		right, err := p.parseExpression(level + 1)
		if err != nil {
			return nil, err
		}
		left = &node{
			Kind:     "binary",
			Operator: operator.Kind,
			Left:     left,
			Right:    right,
			At:       operator.At,
		}
	}
	return left, nil
}

func (p *parser) parseUnary() (*node, error) {
	current := p.peek()
	if current.Kind == "-" || current.Kind == "~" {
		p.take()
		operand, err := p.parseUnary()
		if err != nil {
			return nil, err
		}
		return &node{Kind: "unary", Operator: current.Kind, Left: operand, At: current.At}, nil
	}
	return p.parsePrimary()
}

func (p *parser) parsePrimary() (*node, error) {
	current := p.peek()
	if current.Kind == "int" {
		p.take()
		return &node{Kind: "literal", Value: current.Value, At: current.At}, nil
	}
	if current.Kind == "ident" {
		p.take()
		return &node{Kind: "name", Name: current.Text, At: current.At}, nil
	}
	if current.Kind == "(" {
		p.depth++
		if p.depth > p.maxDepth {
			return nil, &ProgramError{Code: "DEPTH", At: current.At}
		}
		p.take()
		inner, err := p.parseExpression(0)
		if err != nil {
			return nil, err
		}
		if _, err := p.expect(")"); err != nil {
			return nil, err
		}
		p.depth--
		return inner, nil
	}
	return nil, &ProgramError{Code: "PARSE", At: current.At}
}

func parseProgram(text string, maxDepth int) (*program, error) {
	tokens, err := tokenize(text)
	if err != nil {
		return nil, err
	}
	return newParser(tokens, maxDepth).parseProgram()
}
