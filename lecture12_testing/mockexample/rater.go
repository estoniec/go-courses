package mockexample

//go:generate go run go.uber.org/mock/mockgen -source=rater.go -destination=rater_mock_test.go -package=mockexample

type Rater interface {
	Rate(postcode string) (int, error)
}
