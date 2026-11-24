package lecture

import (
	"errors"
	"net/http"
	"net/url"
	"testing"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) {
	return f(r)
}

func TestHTTPTransportFailure(t *testing.T) {
	unavailable := errors.New("transport unavailable")
	calls := 0
	client := &http.Client{Transport: roundTripFunc(func(r *http.Request) (*http.Response, error) {
		calls++
		if r.URL.Path != "/quote" {
			t.Errorf("path = %q, want /quote", r.URL.Path)
		}
		return nil, unavailable
	})}
	_, err := client.Get("https://example.invalid/quote")
	if !errors.Is(err, unavailable) {
		t.Fatalf("error = %v, want the transport error", err)
	}
	if urlErr, ok := errors.AsType[*url.Error](err); !ok || urlErr.Op != "Get" {
		t.Fatalf("expected url.Error for Get, got %v", err)
	}
	if calls != 1 {
		t.Fatalf("calls = %d, want 1", calls)
	}
}
