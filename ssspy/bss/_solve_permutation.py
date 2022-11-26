import functools
import itertools
from typing import Callable, Optional

import numpy as np

from ._flooring import identity, max_flooring

EPS = 1e-12


def correlation_based_permutation_solver(
    separated: np.ndarray,
    demix_filter: np.ndarray = None,
    flooring_fn: Optional[Callable[[np.ndarray], np.ndarray]] = functools.partial(
        max_flooring, eps=EPS
    ),
    overwrite: bool = True,
) -> np.ndarray:
    r"""Solve permutaion of estimated spectrograms.

        Group channels at each frequency bin according to correlations
        between frequencies [#sawada2010underdetermined]_.

    Args:
        separated (numpy.ndarray):
            Separated spectrograms with shape of (n_sources, n_bins, n_frames).
        demix_filter (numpy.ndarray):
            Demixing filters with shape of (n_bins, n_sources, n_channels).
        flooring_fn (callable, optional):
            A flooring function for numerical stability.
            This function is expected to receive (n_channels, n_bins, n_frames)
            and return (n_channels, n_bins, n_frames).
            If you explicitly set ``flooring_fn=None``, \
            the identity function (``lambda x: x``) is used.
            Default: ``partial(max_flooring, eps=1e-15)``.
        overwrite (bool):
            Overwrite ``demix_filter`` if ``overwrite=True``. \
            Default: ``True``.

    Returns:
        numpy.ndarray:
            Permutated demixing filters with shape of (n_bins, n_sources, n_channels).

        .. [#sawada2010underdetermined]
            H. Sawada, S. Araki, and S. Makino,
            "Underdetermined convolutive blind source separation \
            via frequency bin-wise clustering and permutation alignment,"
            in *IEEE Trans. ASLP*, vol. 19, no. 3, pp. 516-527, 2010.
    """
    Y = separated

    if overwrite:
        W = demix_filter
    else:
        W = demix_filter.copy()

    if flooring_fn is None:
        flooring_fn = identity
    else:
        flooring_fn = flooring_fn

    n_bins, _, n_sources = W.shape

    permutations = list(itertools.permutations(range(n_sources)))

    P = np.abs(Y).transpose(1, 0, 2)
    norm = np.sqrt(np.sum(P**2, axis=1, keepdims=True))
    norm = flooring_fn(norm)
    P = P / norm
    correlation = np.sum(P @ P.transpose(0, 2, 1), axis=(1, 2))
    indices = np.argsort(correlation)

    min_idx = indices[0]
    P_criteria = P[min_idx]

    for bin_idx in range(1, n_bins):
        min_idx = indices[bin_idx]
        P_max = None
        perm_max = None

        for perm in permutations:
            P_perm = np.sum(P_criteria * P[min_idx, perm, :])

            if P_max is None or P_perm > P_max:
                P_max = P_perm
                perm_max = perm

        P_criteria = P_criteria + P[min_idx, perm_max, :]
        W[min_idx, :, :] = W[min_idx, perm_max, :]

    return W
