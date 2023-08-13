import os
import sys
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pytest
import scipy.signal as ss

from ssspy.bss.ilrma import GGDILRMA, TILRMA, GaussILRMA, ILRMABase

ssspy_tests_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.append(ssspy_tests_dir)

from dummy.callback import DummyCallback, dummy_function  # noqa: E402
from dummy.utils.dataset import download_sample_speech_data  # noqa: E402

max_duration = 0.5
n_fft = 512
hop_length = 256
n_bins = n_fft // 2 + 1
n_iter = 3
rng = np.random.default_rng(42)

parameters_dof = [100]
parameters_beta = [0.5, 1.5]
parameters_spatial_algorithm = ["IP", "IP1", "IP2", "ISS", "ISS1", "ISS2", "IPA"]
parameters_source_algorithm = ["MM", "ME"]
parameters_callbacks = [None, dummy_function, [DummyCallback(), dummy_function]]
parameters_scale_restoration = [True, False, "projection_back", "minimal_distortion_principle"]
parameters_ilrma_base = [2]
parameters_ilrma_latent = [
    (
        2,
        4,
        2,
        {
            "demix_filter": np.tile(np.eye(2, dtype=np.complex128), (n_bins, 1, 1)),
            "latent": rng.random((2, 4)),
            "basis": rng.random((n_bins, 4)),
        },
    ),
    (3, 3, 1, {}),
]
parameters_ilrma_wo_latent = [
    (
        2,
        2,
        2,
        {
            "demix_filter": np.tile(np.eye(2, dtype=np.complex128), (n_bins, 1, 1)),
            "basis": rng.random((2, n_bins, 2)),
        },
    ),
    (
        3,
        1,
        1,
        {},
    ),
]
parameters_normalization_latent = [True, False, "power"]
parameters_normalization_wo_latent = [True, False, "power", "projection_back"]


@pytest.mark.parametrize(
    "n_basis",
    parameters_ilrma_base,
)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_ilrma_base(
    n_basis: int,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    scale_restoration: Union[str, bool],
):
    ilrma = ILRMABase(
        n_basis,
        partitioning=True,
        callbacks=callbacks,
        scale_restoration=scale_restoration,
        rng=np.random.default_rng(42),
    )

    print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_latent,
)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_gauss_ilrma_latent(
    n_sources: int,
    n_basis: int,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": True,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if source_algorithm == "ME" and domain != 2:
        with pytest.raises(AssertionError) as e:
            ilrma = GaussILRMA(n_basis, **kwargs)

        assert str(e.value) == "domain parameter should be 2 when you specify ME algorithm."
    else:
        ilrma = GaussILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_wo_latent,
)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_wo_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_gauss_ilrma_wo_latent(
    n_sources: int,
    n_basis: int,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": False,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if source_algorithm == "ME" and domain != 2:
        with pytest.raises(AssertionError) as e:
            ilrma = GaussILRMA(n_basis, **kwargs)

        assert str(e.value) == "domain parameter should be 2 when you specify ME algorithm."
    else:
        ilrma = GaussILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_latent,
)
@pytest.mark.parametrize("dof", parameters_dof)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_t_ilrma_latent(
    n_sources: int,
    n_basis: int,
    dof: float,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "dof": dof,
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": True,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if spatial_algorithm == "IPA":
        with pytest.raises(ValueError) as e:
            ilrma = TILRMA(n_basis, **kwargs)

        assert str(e.value) == "IPA is not supported for t-ILRMA."
    elif source_algorithm == "ME" and domain != 2:
        with pytest.raises(AssertionError) as e:
            ilrma = TILRMA(n_basis, **kwargs)

        assert str(e.value) == "domain parameter should be 2 when you specify ME algorithm."
    else:
        ilrma = TILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_wo_latent,
)
@pytest.mark.parametrize("dof", parameters_dof)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_wo_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_t_ilrma_wo_latent(
    n_sources: int,
    n_basis: int,
    dof: float,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "dof": dof,
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": False,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if spatial_algorithm == "IPA":
        with pytest.raises(ValueError) as e:
            ilrma = TILRMA(n_basis, **kwargs)

        assert str(e.value) == "IPA is not supported for t-ILRMA."
    elif source_algorithm == "ME" and domain != 2:
        with pytest.raises(AssertionError) as e:
            ilrma = TILRMA(n_basis, **kwargs)

        assert str(e.value) == "domain parameter should be 2 when you specify ME algorithm."
    else:
        ilrma = TILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_latent,
)
@pytest.mark.parametrize("beta", parameters_beta)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_ggd_ilrma_latent(
    n_sources: int,
    n_basis: int,
    beta: float,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "beta": beta,
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": True,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if source_algorithm == "ME":
        with pytest.raises(AssertionError) as e:
            ilrma = GGDILRMA(n_basis, **kwargs)

        assert str(e.value) == "Not support {}.".format(source_algorithm)
    elif spatial_algorithm == "IPA":
        with pytest.raises(ValueError) as e:
            ilrma = GGDILRMA(n_basis, **kwargs)

        assert str(e.value) == "IPA is not supported for GGD-ILRMA."
    else:
        ilrma = GGDILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain, reset_kwargs",
    parameters_ilrma_wo_latent,
)
@pytest.mark.parametrize("beta", parameters_beta)
@pytest.mark.parametrize("spatial_algorithm", parameters_spatial_algorithm)
@pytest.mark.parametrize("source_algorithm", parameters_source_algorithm)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_wo_latent)
@pytest.mark.parametrize("scale_restoration", parameters_scale_restoration)
def test_ggd_ilrma_wo_latent(
    n_sources: int,
    n_basis: int,
    beta: float,
    spatial_algorithm: str,
    source_algorithm: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    scale_restoration: Union[str, bool],
    reset_kwargs: Dict[str, Any],
):
    if spatial_algorithm in ["IP", "ISS"] and not pytest.run_redundant:
        pytest.skip(reason="Need --run-redundant option to run.")

    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img, _ = download_sample_speech_data(
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_duration=max_duration,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    kwargs = {
        "beta": beta,
        "spatial_algorithm": spatial_algorithm,
        "source_algorithm": source_algorithm,
        "domain": domain,
        "partitioning": False,
        "callbacks": callbacks,
        "normalization": normalization,
        "scale_restoration": scale_restoration,
        "rng": np.random.default_rng(42),
    }

    if source_algorithm == "ME":
        with pytest.raises(AssertionError) as e:
            ilrma = GGDILRMA(n_basis, **kwargs)

        assert str(e.value) == "Not support {}.".format(source_algorithm)
    elif spatial_algorithm == "IPA":
        with pytest.raises(ValueError) as e:
            ilrma = GGDILRMA(n_basis, **kwargs)

        assert str(e.value) == "IPA is not supported for GGD-ILRMA."
    else:
        ilrma = GGDILRMA(n_basis, **kwargs)
        spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter, **reset_kwargs)

        assert spectrogram_mix.shape == spectrogram_est.shape
        assert type(ilrma.loss[-1]) is float

        if spatial_algorithm in ["ISS", "ISS1", "ISS2"]:
            assert ilrma.demix_filter is None

        print(ilrma)
