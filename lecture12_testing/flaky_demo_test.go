//go:build lecture_demo

package lecture

import "testing"

var sharedOrders = map[string]bool{}

func TestFlakyCreateOrder(t *testing.T) {
	sharedOrders["order-1"] = true
}

func TestFlakyInitiallyEmpty(t *testing.T) {
	if len(sharedOrders) != 0 {
		t.Fatal("another test left orders in the shared map")
	}
}
