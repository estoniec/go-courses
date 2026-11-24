package lecture

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

var updateGolden = flag.Bool("update-golden", false, "update reviewed golden responses")

func ExampleShipping() {
	fee, err := Shipping(3000)
	fmt.Println(fee, err)
	// Output: 0 <nil>
}

func requireFee(t *testing.T, total, want int) {
	t.Helper()
	got, err := Shipping(total)
	if err != nil || got != want {
		t.Fatalf("Shipping(%d) = (%d, %v), want (%d, nil)", total, got, err, want)
	}
}

func TestShippingParallel(t *testing.T) {
	for _, tc := range []struct {
		name        string
		total, want int
	}{
		{"paid", 2999, 300},
		{"free", 3000, 0},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			requireFee(t, tc.total, tc.want)
		})
	}
}

func TestTemporaryFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "quote.json")
	if err := os.WriteFile(path, []byte("{\"fee\":300}\n"), 0600); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var quote struct{ Fee int }
	if err := json.Unmarshal(data, &quote); err != nil {
		t.Fatal(err)
	}
	if quote.Fee != 300 {
		t.Fatalf("fee = %d, want 300", quote.Fee)
	}
}

func TestSetenv(t *testing.T) {
	// Setenv restores the original value when this test ends.
	t.Setenv("LECTURE_REGION", "north")
	if got := os.Getenv("LECTURE_REGION"); got != "north" {
		t.Fatalf("region = %q, want north", got)
	}
}

func TestQuoteGolden(t *testing.T) {
	rec := httptest.NewRecorder()
	Quote(rec, httptest.NewRequest("GET", "/quote?total=2999", nil))
	got := rec.Body.Bytes()
	const path = "testdata/quote.golden.json"
	if *updateGolden {
		if err := os.WriteFile(path, got, 0644); err != nil {
			t.Fatal(err)
		}
	}
	want, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Fatalf("response differs\ngot  %q\nwant %q", got, want)
	}
}

func TestWrappedFileError(t *testing.T) {
	path := filepath.Join(t.TempDir(), "missing.json")
	_, err := os.ReadFile(path)
	if err == nil {
		t.Fatal("expected a missing file error")
	}
	err = fmt.Errorf("load quote fixture: %w", err)
	if !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("error = %v, want ErrNotExist in the chain", err)
	}
	if pathErr, ok := errors.AsType[*os.PathError](err); !ok || pathErr.Path != path {
		t.Fatalf("expected PathError for %q, got %v", path, err)
	}
}

func TestDetailedFixtureValidation(t *testing.T) {
	if testing.Short() {
		t.Skip("detailed fixture validation is excluded from the short run")
	}
	data, err := os.ReadFile("testdata/quote.golden.json")
	if err != nil {
		t.Fatal(err)
	}
	if !json.Valid(data) {
		t.Fatal("golden fixture is not valid JSON")
	}
	t.Log("detailed fixture validation completed")
}
