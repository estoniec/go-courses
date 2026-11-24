package lifecycle

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

var fixtureDir string

func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "lecture-package-")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fixtureDir = dir
	code := m.Run()
	if err := os.RemoveAll(dir); err != nil {
		fmt.Fprintln(os.Stderr, err)
		code = 1
	}
	os.Exit(code)
}

func TestSharedFixture(t *testing.T) {
	// Each test gets its own file inside the package-wide temporary resource.
	path := filepath.Join(fixtureDir, t.Name()+".txt")
	if err := os.WriteFile(path, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(path)
	if err != nil || string(got) != "fixture" {
		t.Fatalf("fixture = %q, err = %v", got, err)
	}
}
