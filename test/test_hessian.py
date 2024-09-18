"""Contains tests for ``curvlinops/hessian``."""

from collections.abc import MutableMapping

from numpy import random
from pytest import mark, raises
from torch import block_diag, rand

from curvlinops import HessianLinearOperator
from curvlinops.examples.functorch import functorch_hessian
from curvlinops.examples.utils import report_nonclose
from curvlinops.utils import split_list


def test_HessianLinearOperator_matvec(case, adjoint: bool, scipy_frontend: bool):
    model_func, loss_func, params, data, batch_size_fn = case

    # Test when X is dict-like but batch_size_fn = None (default)
    if isinstance(data[0][0], MutableMapping):
        with raises(ValueError):
            op = HessianLinearOperator(model_func, loss_func, params, data)

    op = HessianLinearOperator(
        model_func, loss_func, params, data, batch_size_fn=batch_size_fn
    )
    op_functorch = functorch_hessian(model_func, loss_func, params, data, input_key="x")

    if scipy_frontend:
        op = op.to_scipy()
        op_functorch = op_functorch.detach().cpu().numpy()

    if adjoint:
        op, op_functorch = op.adjoint(), op_functorch.conj().T

    x = (
        random.rand(op.shape[1])
        if scipy_frontend
        else rand(op.shape[1], dtype=op.dtype, device=op.device)
    )
    report_nonclose(op @ x, op_functorch @ x, atol=1e-7, rtol=1e-4)


def test_HessianLinearOperator_matmat(
    case, adjoint: bool, scipy_frontend: bool, num_vecs: int = 3
):
    model_func, loss_func, params, data, batch_size_fn = case

    op = HessianLinearOperator(
        model_func, loss_func, params, data, batch_size_fn=batch_size_fn
    )
    op_functorch = functorch_hessian(model_func, loss_func, params, data, input_key="x")

    if scipy_frontend:
        op = op.to_scipy()
        op_functorch = op_functorch.detach().cpu().numpy()

    if adjoint:
        op, op_functorch = op.adjoint(), op_functorch.conj().T

    X = (
        random.rand(op.shape[1], num_vecs)
        if scipy_frontend
        else rand(op.shape[1], num_vecs, dtype=op.dtype, device=op.device)
    )
    report_nonclose(op @ X, op_functorch @ X, atol=1e-6, rtol=1e-4)


BLOCKING_FNS = {
    "per-parameter": lambda params: [1 for _ in range(len(params))],
    "two-blocks": lambda params: (
        [1] if len(params) == 1 else [len(params) // 2, len(params) - len(params) // 2]
    ),
}


@mark.parametrize("blocking", BLOCKING_FNS.keys(), ids=BLOCKING_FNS.keys())
def test_blocked_HessianLinearOperator_matmat(
    case, adjoint: bool, blocking: str, scipy_frontend: bool, num_vecs: int = 2
):
    """Test matrix-matrix multiplication with the block-diagonal Hessian.

    Args:
        case: Tuple of model, loss function, parameters, and data.
        adjoint: Whether to test the adjoint operator.
        blocking: Blocking scheme.
        scipy_frontend: Whether to feed SciPy vectors as inputs. If `False`,
            PyTorch vectors are used.
        num_vecs: Number of vectors to multiply with. Default is ``2``.
    """
    model_func, loss_func, params, data, batch_size_fn = case
    block_sizes = BLOCKING_FNS[blocking](params)

    op = HessianLinearOperator(
        model_func,
        loss_func,
        params,
        data,
        batch_size_fn=batch_size_fn,
        in_blocks=block_sizes,
        out_blocks=block_sizes,
    )

    # compute the blocks with functorch and build the block diagonal matrix
    op_functorch = [
        functorch_hessian(model_func, loss_func, params_block, data, input_key="x")
        for params_block in split_list(params, block_sizes)
    ]
    op_functorch = block_diag(*op_functorch)

    if scipy_frontend:
        op = op.to_scipy()
        op_functorch = op_functorch.detach().cpu().numpy()

    if adjoint:
        op, op_functorch = op.adjoint(), op_functorch.conj().T

    X = (
        random.rand(op.shape[1], num_vecs)
        if scipy_frontend
        else rand(op.shape[1], num_vecs, dtype=op.dtype, device=op.device)
    )
    report_nonclose(op @ X, op_functorch @ X, atol=1e-6, rtol=5e-4)
