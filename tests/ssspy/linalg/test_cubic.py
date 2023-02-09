import numpy as np

from ssspy.linalg import cbrt


def test_cbrt():
    rng = np.random.default_rng(0)
    n_bins = 8
    n_channels = 4

    x = rng.standard_normal((n_bins, n_channels))
    y = cbrt(x)

    assert np.allclose(y**3, x)
