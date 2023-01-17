import functools
from typing import Callable, List, Optional, Union

import numpy as np

from ..algorithm.permutation_alignment import correlation_based_permutation_solver
from ..linalg.quadratic import quadratic
from ..special.flooring import max_flooring
from ..special.logsumexp import logsumexp
from ..special.softmax import softmax
from ._psd import to_psd
from .base import IterativeMethodBase

EPS = 1e-10


class CACGMMbase(IterativeMethodBase):
    r"""Base class of complex angular central Gaussian mixture model (cACGMM).

    Args:
        n_sources (int, optional):
            Number of sources to be separated.
            If ``None`` is given, ``n_sources`` is determined by number of channels
            in input spectrogram. Default: ``None``.
        callbacks (callable or list[callable], optional):
            Callback functions. Each function is called before separation and at each iteration.
            Default: ``None``.
        record_loss (bool):
            Record the loss at each iteration of the update algorithm if ``record_loss=True``.
            Default: ``True``.
        rng (numpy.random.Generator, optioinal):
            Random number generator. This is mainly used to randomly initialize parameters
            of cACGMM. If ``None`` is given, ``np.random.default_rng()`` is used.
            Default: ``None``.
    """

    def __init__(
        self,
        n_sources: Optional[int] = None,
        callbacks: Optional[
            Union[
                Callable[["CACGMMbase"], None],
                List[Callable[["CACGMMbase"], None]],
            ]
        ] = None,
        record_loss: bool = True,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.normalization: bool

        super().__init__(callbacks=callbacks, record_loss=record_loss)

        self.n_sources = n_sources

        if rng is None:
            rng = np.random.default_rng()

        self.rng = rng

    def __call__(
        self, input: np.ndarray, n_iter: int = 100, initial_call: bool = True, **kwargs
    ) -> np.ndarray:
        r"""Separate a frequency-domain multichannel signal.

        Args:
            input (numpy.ndarray):
                The mixture signal in frequency-domain.
                The shape is (n_channels, n_bins, n_frames).
            n_iter (int):
                The number of iterations of demixing filter updates.
                Default: ``100``.
            initial_call (bool):
                If ``True``, perform callbacks (and computation of loss if necessary)
                before iterations.

        Returns:
            numpy.ndarray of the separated signal in frequency-domain.
            The shape is (n_channels, n_bins, n_frames).
        """
        self.input = input.copy()

        self._reset(**kwargs)

        raise NotImplementedError("Implement '__call__' method.")

    def __repr__(self) -> str:
        s = "CACGMM("

        if self.n_sources is not None:
            s += "n_sources={n_sources}, "

        s += "record_loss={record_loss}"

        s += ")"

        return s.format(**self.__dict__)

    def _reset(self, **kwargs) -> None:
        r"""Reset attributes by given keyword arguments.

        Args:
            kwargs:
                Keyword arguments to set as attributes of CACGMM.
        """
        assert self.input is not None, "Specify data!"

        for key in kwargs.keys():
            setattr(self, key, kwargs[key])

        X = self.input

        norm = np.linalg.norm(X, axis=0)
        Z = X / norm
        self.unit_input = Z

        n_sources = self.n_sources
        n_channels, n_bins, n_frames = X.shape

        if n_sources is None:
            n_sources = n_channels

        self.n_sources, self.n_channels = n_sources, n_channels
        self.n_bins, self.n_frames = n_bins, n_frames

        self._init_parameters(rng=self.rng)

    def _init_parameters(self, rng: Optional[np.random.Generator] = None) -> None:
        r"""Initialize parameters of cACGMM.

        Args:
            rng (numpy.random.Generator, optional):
                Random number generator. If ``None`` is given,
                ``np.random.default_rng()`` is used.
                Default: ``None``.
        """
        n_sources, n_channels = self.n_sources, self.n_channels
        n_bins = self.n_bins

        if rng is None:
            rng = np.random.default_rng()

        alpha = rng.random((n_sources, n_bins))
        alpha = alpha / alpha.sum(axis=0)

        eye = np.eye(n_channels, dtype=np.complex128)
        B_diag = self.rng.random((n_sources, n_bins, n_channels))
        B_diag = B_diag / B_diag.sum(axis=-1, keepdims=True)
        B = B_diag[:, :, :, np.newaxis] * eye

        self.mixing = alpha
        self.covariance = B

        # The shape of posterior is (n_sources, n_bins, n_frames).
        # This is always required to satisfy posterior.sum(axis=0) = 1
        self.posterior = None

    def separate(self, input: np.ndarray) -> np.ndarray:
        r"""Separate ``input``.

        Args:
            input (numpy.ndarray):
                The mixture signal in frequency-domain.
                The shape is (n_channels, n_bins, n_frames).

        Returns:
            numpy.ndarray of the separated signal in frequency-domain.
            The shape is (n_sources, n_bins, n_frames).
        """
        raise NotImplementedError("Implement 'separate' method.")

    def normalize_covariance(self) -> None:
        r"""Normalize covariance of cACG.

        .. math::
            \boldsymbol{B}_{in}
            \leftarrow\frac{\boldsymbol{B}_{in}}{\mathrm{tr}(\boldsymbol{B}_{in})}
        """
        assert self.normalization, "Set normalization."

        B = self.covariance

        trace = np.trace(B, axis1=-2, axis2=-1)
        trace = np.real(trace)
        B = B / trace[..., np.newaxis, np.newaxis]

        self.covariance = B

    def compute_loss(self) -> float:
        r"""Compute loss :math:`\mathcal{L}`.

        Returns:
            Computed loss.
        """
        raise NotImplementedError("Implement 'compute_loss' method.")

    def compute_logdet(self, covariance: np.ndarray) -> np.ndarray:
        r"""Compute log-determinant of input.

        Args:
            covariance (numpy.ndarray):
                Covariance matrix with shape of (n_sources, n_bins, n_channels, n_channels).

        Returns:
            numpy.ndarray of log-determinant.
        """
        _, logdet = np.linalg.slogdet(covariance)

        return logdet


class CACGMM(CACGMMbase):
    r"""Complex angular central Gaussian mixture model (cACGMM) [#ito2016complex]_.

    Args:
        n_sources (int, optional):
            Number of sources to be separated.
            If ``None`` is given, ``n_sources`` is determined by number of channels
            in input spectrogram. Default: ``None``.
        flooring_fn (callable, optional):
            A flooring function for numerical stability.
            This function is expected to return the same shape tensor as the input.
            If you explicitly set ``flooring_fn=None``,
            the identity function (``lambda x: x``) is used.
        callbacks (callable or list[callable], optional):
            Callback functions. Each function is called before separation and at each iteration.
            Default: ``None``.
        normalization (bool):
            If ``True`` is given, normalization is applied to covariance in cACG.
        solve_permutation (bool):
            If ``solve_permutation=True``, a permutation solver is used to align
            estimated spectrograms. Default: ``True``.
        record_loss (bool):
            Record the loss at each iteration of the update algorithm if ``record_loss=True``.
            Default: ``True``.
        reference_id (int):
            Reference channel to extract separated signals. Default: ``0``.
        rng (numpy.random.Generator, optioinal):
            Random number generator. This is mainly used to randomly initialize parameters
            of cACGMM. If ``None`` is given, ``np.random.default_rng()`` is used.
            Default: ``None``.

    .. note::
        The estimated spectrograms are aligned by similarity of their power.

    .. [#ito2016complex] N. Ito, S. Araki, and T. Nakatani. \
        "Complex angular central Gaussian mixture model for directional statistics \
        in mask-based microphone array signal processing,"
        in *Proc. EUSIPCO*, 2016, pp. 1153-1157.
    """

    def __init__(
        self,
        n_sources: Optional[int] = None,
        flooring_fn: Optional[Callable[[np.ndarray], np.ndarray]] = functools.partial(
            max_flooring, eps=EPS
        ),
        callbacks: Optional[
            Union[
                Callable[["CACGMM"], None],
                List[Callable[["CACGMM"], None]],
            ]
        ] = None,
        normalization: bool = True,
        solve_permutation: bool = True,
        record_loss: bool = True,
        reference_id: int = 0,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        super().__init__(n_sources=n_sources, callbacks=callbacks, record_loss=record_loss, rng=rng)

        self.flooring_fn = flooring_fn
        self.normalization = normalization
        self.solve_permutation = solve_permutation
        self.reference_id = reference_id

    def __call__(
        self, input: np.ndarray, n_iter: int = 100, initial_call: bool = True, **kwargs
    ) -> np.ndarray:
        r"""Separate a frequency-domain multichannel signal.

        Args:
            input (numpy.ndarray):
                The mixture signal in frequency-domain.
                The shape is (n_channels, n_bins, n_frames).
            n_iter (int):
                The number of iterations of demixing filter updates.
                Default: ``100``.
            initial_call (bool):
                If ``True``, perform callbacks (and computation of loss if necessary)
                before iterations.

        Returns:
            numpy.ndarray of the separated signal in frequency-domain.
            The shape is (n_channels, n_bins, n_frames).
        """
        self.input = input.copy()

        self._reset(**kwargs)

        # Call __call__ of CACGMMbase's parent, i.e. __call__ of IterativeMethodBase
        super(CACGMMbase, self).__call__(n_iter=n_iter, initial_call=initial_call)

        # posterior should be updated
        self.update_posterior()

        X = self.input
        Y = self.separate(X, posterior=self.posterior)

        if self.solve_permutation:
            # TODO: clustering priors instead of spectrogram.
            alpha = self.mixing
            B = self.covariance
            gamma = self.posterior

            alpha = alpha.transpose(1, 0)
            B = B.transpose(1, 0, 2, 3)
            gamma = gamma.transpose(1, 0, 2)
            Y = Y.transpose(1, 0, 2)
            Y, (alpha, B, gamma) = correlation_based_permutation_solver(
                Y, alpha, B, gamma, flooring_fn=self.flooring_fn
            )
            alpha = alpha.transpose(1, 0)
            B = B.transpose(1, 0, 2, 3)
            gamma = gamma.transpose(1, 0, 2)
            Y = Y.transpose(1, 0, 2)

            self.mixing = alpha
            self.covariance = B
            self.posterior = gamma

        self.output = Y

        return self.output

    def __repr__(self) -> str:
        s = "CACGMM("

        if self.n_sources is not None:
            s += "n_sources={n_sources}, "

        s += "record_loss={record_loss}"
        s += ", normalization={normalization}"
        s += ", solve_permutation={solve_permutation}"
        s += ", reference_id={reference_id}"

        s += ")"

        return s.format(**self.__dict__)

    def separate(self, input: np.ndarray, posterior: Optional[np.ndarray] = None) -> np.ndarray:
        r"""Separate ``input`` using posterior probabilities.

        In this method, ``self.posterior`` is not updated.

        Args:
            input (numpy.ndarray):
                The mixture signal in frequency-domain.
                The shape is (n_channels, n_bins, n_frames).
            posterior (numpy.ndarray, optional):
                Posterior probability. If not specified, ``posterior`` is computed by current
                parameters.

        Returns:
            numpy.ndarray of the separated signal in frequency-domain.
            The shape is (n_sources, n_bins, n_frames).
        """
        X = input

        if posterior is None:
            alpha = self.mixing
            Z = self.unit_input
            B = self.covariance

            Z = Z.transpose(1, 2, 0)
            B_inverse = np.linalg.inv(B)
            ZBZ = quadratic(Z, B_inverse[:, :, np.newaxis])
            ZBZ = np.real(ZBZ)
            ZBZ = np.maximum(ZBZ, 0)
            ZBZ = self.flooring_fn(ZBZ)

            log_alpha = np.log(alpha)
            _, logdet = np.linalg.slogdet(B)
            log_prob = log_alpha - logdet
            log_gamma = log_prob[:, :, np.newaxis] - self.n_channels * np.log(ZBZ)

            gamma = softmax(log_gamma, axis=0)
        else:
            gamma = posterior

        return gamma * X[self.reference_id]

    def update_once(self) -> None:
        r"""Perform E and M step once.

        In ``update_posterior``, posterior probabilities are updated, which corresponds to E step.
        In ``update_parameters``, parameters of cACGMM are updated, which corresponds to M step.
        """
        self.update_posterior()
        self.update_parameters()

        if self.normalization:
            self.normalize_covariance()

    def update_posterior(self) -> None:
        r"""Update posteriors.

        This method corresponds to E step in EM algorithm for cACGMM.
        """
        alpha = self.mixing
        Z = self.unit_input
        B = self.covariance

        Z = Z.transpose(1, 2, 0)
        B_inverse = np.linalg.inv(B)
        ZBZ = quadratic(Z, B_inverse[:, :, np.newaxis])
        ZBZ = np.real(ZBZ)
        ZBZ = np.maximum(ZBZ, 0)
        ZBZ = self.flooring_fn(ZBZ)

        log_prob = np.log(alpha) - self.compute_logdet(B)
        log_gamma = log_prob[:, :, np.newaxis] - self.n_channels * np.log(ZBZ)

        gamma = softmax(log_gamma, axis=0)

        self.posterior = gamma

    def update_parameters(self) -> None:
        r"""Update parameters of mixture of complex angular central Gaussian distributions.

        This method corresponds to M step in EM algorithm for cACGMM.
        """
        Z = self.unit_input
        B = self.covariance
        gamma = self.posterior

        Z = Z.transpose(1, 2, 0)
        B_inverse = np.linalg.inv(B)
        ZBZ = quadratic(Z, B_inverse[:, :, np.newaxis])
        ZBZ = np.real(ZBZ)
        ZBZ = np.maximum(ZBZ, 0)
        ZBZ = self.flooring_fn(ZBZ)
        ZZ = Z[:, :, :, np.newaxis] * Z[:, :, np.newaxis, :].conj()

        alpha = np.mean(gamma, axis=-1)

        GZBZ = gamma / ZBZ
        num = np.sum(GZBZ[:, :, :, np.newaxis, np.newaxis] * ZZ, axis=2)
        denom = np.sum(gamma, axis=2)
        B = self.n_channels * (num / denom[:, :, np.newaxis, np.newaxis])
        B = to_psd(B, flooring_fn=self.flooring_fn)

        self.mixing = alpha
        self.covariance = B

    def compute_loss(self) -> float:
        r"""Compute loss of cACGMM :math:`\mathcal{L}`.

        :math:`\mathcal{L}` is defined as follows:

        .. math::
            \mathcal{L}
            = -\frac{1}{J}\sum_{i,j}\log\left(
            \sum_{n}\frac{\alpha_{in}}{\det\boldsymbol{B}_{in}}
            \frac{1}{(\boldsymbol{z}_{ij}^{\mathsf{H}}\boldsymbol{B}_{in}^{-1}\boldsymbol{z}_{ij})^{M}}
            \right).
        """
        alpha = self.mixing
        Z = self.unit_input
        B = self.covariance

        Z = Z.transpose(1, 2, 0)
        B_inverse = np.linalg.inv(B)
        ZBZ = quadratic(Z, B_inverse[:, :, np.newaxis])
        ZBZ = np.real(ZBZ)
        ZBZ = np.maximum(ZBZ, 0)
        ZBZ = self.flooring_fn(ZBZ)

        log_prob = np.log(alpha) - self.compute_logdet(B)
        log_gamma = log_prob[:, :, np.newaxis] - self.n_channels * np.log(ZBZ)

        loss = -logsumexp(log_gamma, axis=0)
        loss = np.mean(loss, axis=-1)
        loss = loss.sum(axis=0)
        loss = loss.item()

        return loss