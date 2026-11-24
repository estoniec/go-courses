package lecture

import (
	"runtime"
	"sync"
	"testing"
	"time"
)

var schedulerBenchmarkResult uint64

// BenchmarkScheduler запускает 64 горутины независимо от GOMAXPROCS.
// Все выполняют вычисления; каждая восьмая периодически засыпает на таймере.
// Так в trace появляются выполняющиеся, готовые к выполнению и ожидающие горутины.
// Одна операция бенчмарка — 50 000 шагов вычисления, всего операций ровно b.N.
// Также каждая операция выделяет около 32 КиБ в куче. Каждая горутина хранит
// последние 8 буферов; при замене старый буфер становится доступен для сборки GC.
// При 64 активных работниках удерживается около 16 МиБ полезных данных.
// GC запускается автоматически; runtime.GC() здесь не вызывается.
// В trace смотри Heap, GC concurrent mark phase и короткие stop-the-world.
// Чтобы GC запускался чаще, можно добавить GOGC=25 перед командой go test.
//
// Сравнение GOMAXPROCS (флаг -cpu меняет его между запусками):
//
//	go test -run '^$' -bench '^BenchmarkScheduler$' -benchtime=2s -count=1 -cpu=1,2,4 .
//
// Для отдельных трассировок лучше отдельные запуски:
//
//	go test -run '^$' -bench '^BenchmarkScheduler$' -benchtime=2s -count=1 -cpu=1 -trace=scheduler-p1.trace .
//	go test -run '^$' -bench '^BenchmarkScheduler$' -benchtime=2s -count=1 -cpu=4 -trace=scheduler-p4.trace .
//
// GOMAXPROCS ограничивает одновременное выполнение Go-кода, а не число горутин.
// Сбор trace влияет на время: сравнивать производительность лучше без -trace.
func BenchmarkScheduler(b *testing.B) {
	const workers = 64
	var results [workers]uint64
	var wg sync.WaitGroup
	start := make(chan struct{})

	wg.Add(workers)
	for worker := 0; worker < workers; worker++ {
		go func(worker int) {
			defer wg.Done()
			<-start

			state := uint64(worker + 1)
			completed := 0
			var retained [8][]byte
			for operation := worker; operation < b.N; operation += workers {
				for step := 0; step < 50_000; step++ {
					state = state*6364136223846793005 + 1
					state ^= state >> 17
				}
				payload := make([]byte, 32*1024+int(state&1023))
				for offset := 0; offset < len(payload); offset += 4096 {
					payload[offset] = byte(state)
				}
				retained[completed%len(retained)] = payload
				completed++
				if worker%8 == 0 && completed%32 == 0 {
					time.Sleep(time.Millisecond)
				}
			}
			runtime.KeepAlive(retained)
			results[worker] = state
		}(worker)
	}
	b.ReportAllocs()
	b.ResetTimer()
	close(start)
	wg.Wait()
	b.StopTimer()

	var result uint64
	for _, value := range results {
		result ^= value
	}
	schedulerBenchmarkResult = result
}
