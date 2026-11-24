package lecture

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/mock"
)

type deliveryRater interface {
	Rate(context.Context, string) (int, error)
}

type deliveryService struct{ rates deliveryRater }

func (s deliveryService) Fee(ctx context.Context, postcode string) (int, error) {
	if postcode == "" {
		return 0, errors.New("postcode is required")
	}
	return s.rates.Rate(ctx, postcode)
}

type raterMock struct{ mock.Mock }

func (m *raterMock) Rate(ctx context.Context, postcode string) (int, error) {
	args := m.Called(ctx, postcode)
	return args.Int(0), args.Error(1)
}

func TestDeliveryMock(t *testing.T) {
	rates := new(raterMock)
	rates.On("Rate", mock.Anything, "101000").Return(300, nil).Once()
	t.Cleanup(func() { rates.AssertExpectations(t) })
	svc := deliveryService{rates: rates}
	fee, err := svc.Fee(context.Background(), "101000")
	if err != nil || fee != 300 {
		t.Fatalf("fee = %d, err = %v, want 300 and nil", fee, err)
	}
}
