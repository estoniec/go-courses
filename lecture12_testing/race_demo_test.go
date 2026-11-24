//go:build lecture_demo

package lecture

import (
	"sync"
	"testing"
)

func TestRaceCounter(t *testing.T) {
	var attempts int
	var wg sync.WaitGroup
	start := make(chan struct{})
	for range 2 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start
			for range 1000 {

				attempts++
			}
		}()
	}
	close(start)
	wg.Wait()
	t.Log(attempts)
}
