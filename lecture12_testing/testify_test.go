package lecture

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestShippingWithTestify(t *testing.T) {
	fee, err := Shipping(3000)
	require.NoError(t, err)
	assert.Equal(t, 0, fee)
}
