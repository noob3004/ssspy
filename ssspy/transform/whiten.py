import numpy as np


def whiten(input: np.ndarray) -> np.ndarray:
    r"""Apply whitening (a.k.a sphering).

    Args:
        input (numpy.ndarray):
            If input is 2D real tensor, it is regarded as (n_channels, n_samples).
            If input is 3D complex tensor, it is regarded as (n_channels, n_bins, n_frames).
            If input is 3D real tensor, it is regarded as (batch_size, n_channels, n_samples).
            If input is 4D complex tensor, \
            it is regarded as (batch_size, n_channels, n_bins, n_frames).

    Returns:
        Whitened tensor.
        The type (real or complex) and shape is same as input.
    """
    if input.ndim == 2:
        if np.iscomplexobj(input):
            raise ValueError("Real tensor is expected, but given complex tensor.")
        else:
            n_channels = input.shape[0]
            X = input.transpose(1, 0)
            covariance = np.mean(X[:, :, np.newaxis] * X[:, np.newaxis, :], axis=0)
            W, V = np.linalg.eigh(covariance)
            D_diag = 1 / np.sqrt(W)
            D_diag = np.diag(D_diag)
            V_transpose = V.transpose(1, 0)
            output = D_diag @ V_transpose @ X.transpose(1, 0)
    elif input.ndim == 3:
        if np.iscomplexobj(input):
            n_channels = input.shape[0]
            X = input.transpose(1, 2, 0)
            covariance = np.mean(X[:, :, :, np.newaxis] * X[:, :, np.newaxis, :].conj(), axis=1)
            W, V = np.linalg.eigh(covariance)
            D_diag = 1 / np.sqrt(W)
            D_diag = D_diag[:, :, np.newaxis]
            D_diag = D_diag * np.eye(n_channels)
            V_Hermite = V.transpose(0, 2, 1).conj()
            Y = D_diag @ V_Hermite @ X.transpose(0, 2, 1)
            output = Y.transpose(1, 0, 2)
        else:
            n_channels = input.shape[1]
            X = input.transpose(0, 2, 1)
            covariance = np.mean(X[:, :, :, np.newaxis] * X[:, :, np.newaxis, :], axis=1)
            W, V = np.linalg.eigh(covariance)
            D_diag = 1 / np.sqrt(W)
            D_diag = D_diag[:, :, np.newaxis]
            D_diag = D_diag * np.eye(n_channels)
            V_transpose = V.transpose(0, 2, 1)
            output = D_diag @ V_transpose @ X.transpose(0, 2, 1)
    elif input.ndim == 4:
        if np.iscomplexobj(input):
            n_channels = input.shape[1]
            X = input.transpose(0, 2, 3, 1)
            covariance = np.mean(
                X[:, :, :, :, np.newaxis] * X[:, :, :, np.newaxis, :].conj(), axis=2
            )
            W, V = np.linalg.eigh(covariance)
            D_diag = 1 / np.sqrt(W)
            D_diag = D_diag[:, :, :, np.newaxis]
            D_diag = D_diag * np.eye(n_channels)
            V_Hermite = V.transpose(0, 1, 3, 2).conj()
            Y = D_diag @ V_Hermite @ X.transpose(0, 1, 3, 2)
            output = Y.transpose(0, 2, 1, 3)
        else:
            raise ValueError("Complex tensor is expected, but given real tensor.")
    else:
        raise ValueError(
            "The dimension of input is expected 2, 3, or 4, but given {}.".format(input.ndim)
        )

    return output
