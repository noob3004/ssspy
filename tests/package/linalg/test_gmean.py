import numpy as np
import pytest
from scipy.linalg import sqrtm

from ssspy.linalg import gmeanmh

parameters_type = [1, 2, 3]


def gmeanmh_scipy(A: np.ndarray, B: np.ndarray, inverse="left") -> np.ndarray:
    def _sqrtm(X) -> np.ndarray:
        return np.stack([sqrtm(x) for x in X], axis=0)

    if inverse == "left":
        AB = np.linalg.solve(A, B)
        G = A @ _sqrtm(AB)
    elif inverse == "right":
        AB = np.linalg.solve(B, A)
        AB = AB.swapaxes(-2, -1).conj()
        G = _sqrtm(AB) @ B
    else:
        raise ValueError(f"Invalid inverse={inverse} is given.")

    return G


@pytest.mark.parametrize("type", parameters_type)
def test_gmean(type: int):
    rng = np.random.default_rng(0)
    size = (16, 32, 4, 1)

    def create_psd():
        x = rng.random(size) + 1j * rng.random(size)
        XX = x * x.transpose(0, 1, 3, 2).conj()

        return np.mean(XX, axis=0)

    A = create_psd()
    B = create_psd()

    G1 = gmeanmh(A, B, type=type)

    if type == 1:
        assert np.allclose(G1 @ np.linalg.inv(A) @ G1, B)
    elif type == 2:
        assert np.allclose(G1 @ A @ G1, B)
    elif type == 3:
        assert np.allclose(G1 @ np.linalg.inv(A) @ G1, np.linalg.inv(B))
    else:
        raise ValueError("Invalid type={} is given.".format(type))

    if type == 2:
        A = np.linalg.inv(A)
    elif type == 3:
        B = np.linalg.inv(B)

    G2 = gmeanmh_scipy(A, B, inverse="left")
    G3 = gmeanmh_scipy(A, B, inverse="right")

    assert np.allclose(G1, G2)
    assert np.allclose(G1, G3)
