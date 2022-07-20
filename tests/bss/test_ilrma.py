from typing import Optional, Union, Callable, List

import pytest
import numpy as np
import scipy.signal as ss

from ssspy.bss.ilrma import GaussILRMA, TILRMA
from ssspy.utils.dataset import download_sample_speech_data
from tests.dummy.callback import DummyCallback, dummy_function

max_samples = 8000
n_fft = 512
hop_length = 256
n_bins = n_fft // 2 + 1
n_iter = 5
sisec2010_root = "./tests/.data/SiSEC2010"
mird_root = "./tests/.data/MIRD"

parameters_dof = [1, 100]
parameters_algorithm_spatial = ["IP", "IP1", "IP2", "ISS", "ISS1", "ISS2"]
parameters_callbacks = [None, dummy_function, [DummyCallback(), dummy_function]]
parameters_gauss_ilrma_latent = [
    (2, 4, 2),
    (3, 3, 1),
]
parameters_gauss_ilrma_wo_latent = [
    (2, 2, 2),
    (3, 1, 1),
]
parameters_normalization_latent = [True, False, "power"]
parameters_normalization_wo_latent = [True, False, "power", "projection_back"]


@pytest.mark.parametrize(
    "n_sources, n_basis, domain", parameters_gauss_ilrma_latent,
)
@pytest.mark.parametrize("algorithm_spatial", parameters_algorithm_spatial)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_latent)
def test_gauss_ilrma_latent(
    n_sources: int,
    n_basis: int,
    algorithm_spatial: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
):
    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img = download_sample_speech_data(
        sisec2010_root=sisec2010_root,
        mird_root=mird_root,
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_samples=max_samples,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    ilrma = GaussILRMA(
        n_basis,
        algorithm_spatial=algorithm_spatial,
        domain=domain,
        partitioning=True,
        callbacks=callbacks,
        normalization=normalization,
        rng=np.random.default_rng(42),
    )
    spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter)

    assert spectrogram_mix.shape == spectrogram_est.shape

    print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain", parameters_gauss_ilrma_wo_latent,
)
@pytest.mark.parametrize("algorithm_spatial", parameters_algorithm_spatial)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_wo_latent)
def test_gauss_ilrma_wo_latent(
    n_sources: int,
    n_basis: int,
    algorithm_spatial: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
):
    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img = download_sample_speech_data(
        sisec2010_root=sisec2010_root,
        mird_root=mird_root,
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_samples=max_samples,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    ilrma = GaussILRMA(
        n_basis,
        algorithm_spatial=algorithm_spatial,
        domain=domain,
        partitioning=False,
        callbacks=callbacks,
        normalization=normalization,
        rng=np.random.default_rng(42),
    )
    spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter)

    assert spectrogram_mix.shape == spectrogram_est.shape

    print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain", parameters_gauss_ilrma_wo_latent,
)
@pytest.mark.parametrize("dof", parameters_dof)
@pytest.mark.parametrize("algorithm_spatial", parameters_algorithm_spatial)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_latent)
def test_t_ilrma_latent(
    n_sources: int,
    n_basis: int,
    dof: float,
    algorithm_spatial: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
):
    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img = download_sample_speech_data(
        sisec2010_root=sisec2010_root,
        mird_root=mird_root,
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_samples=max_samples,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    ilrma = TILRMA(
        n_basis,
        dof=dof,
        algorithm_spatial=algorithm_spatial,
        domain=domain,
        partitioning=True,
        callbacks=callbacks,
        normalization=normalization,
        rng=np.random.default_rng(42),
    )
    spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter)

    assert spectrogram_mix.shape == spectrogram_est.shape

    print(ilrma)


@pytest.mark.parametrize(
    "n_sources, n_basis, domain", parameters_gauss_ilrma_wo_latent,
)
@pytest.mark.parametrize("dof", parameters_dof)
@pytest.mark.parametrize("algorithm_spatial", parameters_algorithm_spatial)
@pytest.mark.parametrize("callbacks", parameters_callbacks)
@pytest.mark.parametrize("normalization", parameters_normalization_wo_latent)
def test_t_ilrma_wo_latent(
    n_sources: int,
    n_basis: int,
    dof: float,
    algorithm_spatial: str,
    domain: float,
    callbacks: Optional[Union[Callable[[GaussILRMA], None], List[Callable[[GaussILRMA], None]]]],
    normalization: Optional[Union[str, bool]],
    rng=np.random.default_rng(42),
):
    if n_sources < 4:
        sisec2010_tag = "dev1_female3"
    elif n_sources == 4:
        sisec2010_tag = "dev1_female4"
    else:
        raise ValueError("n_sources should be less than 5.")

    waveform_src_img = download_sample_speech_data(
        sisec2010_root=sisec2010_root,
        mird_root=mird_root,
        n_sources=n_sources,
        sisec2010_tag=sisec2010_tag,
        max_samples=max_samples,
        conv=True,
    )
    waveform_mix = np.sum(waveform_src_img, axis=1)  # (n_channels, n_samples)

    _, _, spectrogram_mix = ss.stft(
        waveform_mix, window="hann", nperseg=n_fft, noverlap=n_fft - hop_length
    )

    ilrma = TILRMA(
        n_basis,
        dof=dof,
        algorithm_spatial=algorithm_spatial,
        domain=domain,
        partitioning=False,
        callbacks=callbacks,
        normalization=normalization,
        rng=np.random.default_rng(42),
    )
    spectrogram_est = ilrma(spectrogram_mix, n_iter=n_iter)

    assert spectrogram_mix.shape == spectrogram_est.shape

    print(ilrma)
