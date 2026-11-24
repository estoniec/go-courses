//go:build go1.25

package lecture

import (
	"context"
	"testing"
	"testing/synctest"
	"time"
)

func TestTimeoutSynctest(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		start := time.Now()
		ctx, cancel := context.WithTimeout(t.Context(), 5*time.Minute)
		defer cancel()

		time.Sleep(5*time.Minute - time.Nanosecond)
		synctest.Wait()
		if ctx.Err() != nil {
			t.Fatal("context expired before the deadline")
		}
		time.Sleep(time.Nanosecond)
		synctest.Wait()
		if ctx.Err() != context.DeadlineExceeded {
			t.Fatalf("context error = %v, want DeadlineExceeded", ctx.Err())
		}
		t.Log("virtual elapsed:", time.Since(start))
	})
}

func TestWorkerCancelSynctest(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		ctx, cancel := context.WithCancel(t.Context())
		defer cancel()
		stopped := false
		go func() {
			<-ctx.Done()
			stopped = true
		}()
		synctest.Wait()
		if stopped {
			t.Fatal("worker stopped before cancellation")
		}
		cancel()
		synctest.Wait()
		if !stopped {
			t.Fatal("worker did not stop after cancellation")
		}
	})
}
