"""General utility functions."""

from typing import List

from numpy import cumsum
from torch import Tensor


def split_list(x: List, sizes: List[int]) -> List[List]:
    """Split a list into multiple lists of specified size.

    Args:
        x: List to be split.
        sizes: Sizes of the resulting lists.

    Returns:
        List of lists. Each sub-list has the size specified in ``sizes``.

    Raises:
        ValueError: If the sum of ``sizes`` does not match the input list's length.
    """
    if len(x) != sum(sizes):
        raise ValueError(
            f"List to be split has length {len(x)}, but requested sub-list with a total"
            + f" of {sum(sizes)} entries."
        )
    boundaries = cumsum([0] + sizes)
    return [x[boundaries[i] : boundaries[i + 1]] for i in range(len(sizes))]


def allclose_report(tensor1: Tensor, tensor2: Tensor, rtol: float, atol: float) -> bool:
    """Same as ``allclose``, but prints entries that differ.

    Args:
        tensor1: First tensor for comparison.
        tensor2: Second tensor for comparison.
        rtol: Relative tolerance.
        atol: Absolute tolerance.

    Returns:
        ``True`` if the tensors are close, ``False`` otherwise.
    """
    close = tensor1.allclose(tensor2, rtol=rtol, atol=atol)
    if not close:
        nonclose_idx = tensor1.isclose(tensor2, rtol=rtol, atol=atol).logical_not_()
        for idx, t1, t2 in zip(
            nonclose_idx.argwhere(),
            tensor1[nonclose_idx].flatten(),
            tensor2[nonclose_idx].flatten(),
        ):
            print(f"at index {idx}: {t1:.5e} ≠ {t2:.5e}, ratio: {t1 / t2:.5e}")

    return close
