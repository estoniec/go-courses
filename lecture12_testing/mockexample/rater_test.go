package mockexample

import (
	"testing"

	"go.uber.org/mock/gomock"
)

func TestGeneratedRater(t *testing.T) {
	ctrl := gomock.NewController(t)
	rates := NewMockRater(ctrl)
	rates.EXPECT().Rate("101000").Return(300, nil).Times(1)

	fee, err := rates.Rate("101000")
	if err != nil || fee != 300 {
		t.Fatalf("fee=%d err=%v, want 300 and nil", fee, err)
	}
}
