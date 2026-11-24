package lecture

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
)

// Shipping returns the delivery fee in rubles for a subtotal in rubles.
func Shipping(total int) (int, error) {
	switch {
	case total < 0:
		return 0, errors.New("negative total")
	case total >= 3000:
		return 0, nil
	default:
		return 300, nil
	}
}

func Quote(w http.ResponseWriter, r *http.Request) {
	total, err := strconv.Atoi(r.URL.Query().Get("total"))
	if err != nil {
		http.Error(w, "invalid total", http.StatusBadRequest)
		return
	}
	fee, err := Shipping(total)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(struct {
		Fee int `json:"fee"`
	}{Fee: fee})
}

func ParseSKU(s string) (id int, ok bool) {
	raw, ok := strings.CutPrefix(s, "sku-")
	if !ok {
		return 0, false
	}
	id, err := strconv.Atoi(raw)
	return id, err == nil && id > 0
}

func csvConcat(skus []string) string {
	var out string
	for i, sku := range skus {
		if i > 0 {
			out += ","
		}
		out += sku
	}
	return out
}

func csvJoin(skus []string) string {
	return strings.Join(skus, ",")
}

func exampleSKUs() []string {
	out := make([]string, 200)
	for i := range out {
		out[i] = fmt.Sprintf("sku-%04d", i)
	}
	return out
}
