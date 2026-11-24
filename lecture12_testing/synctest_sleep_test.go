//go:build go1.27

package lecture

import (
	"testing"
	"testing/synctest"
	"time"
)

func TestSynctestSleep(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		done := false
		go func() {
			time.Sleep(time.Second)
			done = true
		}()
		synctest.Sleep(time.Second)
		if !done {
			t.Fatal("scheduled operation did not complete")
		}
	})
}
