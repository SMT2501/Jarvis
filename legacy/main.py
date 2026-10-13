"""
    TASK 1  Data acquisition & cleaning      -> get_returns()
    TASK 2  Estimation module                -> estimate(), Estimates
    TASK 3  Core optimiser (single b)        -> optimize(), unconstrained_weights()
    TASK 4  Sensitivity sweep & breakpoints  -> sensitivity_sweep(), detect_breakpoints()
    TASK 5  Monte Carlo bootstrap            -> bootstrap_sweep(), summarise_bootstrap()
    TASK 6  Separation theorem verification  -> verify_separation(), plot_separation()
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize, LinearConstraint, Bounds
import yfinance as yf


# ============================================================================
# TASK 1 - DATA ACQUISITION & CLEANING
# ============================================================================
# Securities: MTN, Capitec, Naspers, Coronation, SPAR (different sectors, for
# diversification and exposure to different risk drivers).

def get_returns(security_codes, period="1y", interval="1d"):
    """Download adjusted closing prices and return a table of SIMPLE returns.

    auto_adjust=True makes yfinance adjust prices for splits and dividends.
    Returns (P_t - P_{t-1}) / P_{t-1}, one column per ticker, indexed by date.
    The first row is NaN (no previous price); Task 2's clean_returns() drops it
    together with any date on which a security did not trade.
    """
    prices = pd.DataFrame()
    for security in security_codes:
        data = yf.download(security, period=period, interval=interval,
                           auto_adjust=True)
        closing_price = data["Close"].squeeze()   # closing prices only
        closing_price.name = security
        prices = closing_price.to_frame() if prices.empty \
            else prices.join(closing_price, how="outer")

    returns = (prices - prices.shift(1)) / prices.shift(1)
    return returns


# ============================================================================
# TASK 2 - ESTIMATION MODULE
# ============================================================================
# Estimators from Sections 8.5.1 and 9.3.1 of Ross (N = number of observations):
#   r_i    = (1/N)     * sum_k R_ik
#   v_i^2  = (1/(N-1)) * sum_k (R_ik - r_i)^2
#   c(i,j) = (1/(N-1)) * sum_k (R_ik - r_i)(R_jk - r_j)

@dataclass
class Estimates:
    tickers: list          # security names, fixed order
    r: np.ndarray          # (n,)   expected returns r_i
    v2: np.ndarray         # (n,)   variances v_i^2
    C: np.ndarray          # (n, n) covariance matrix (diagonal = variances)
    n_obs: int             # N used
    periods_per_year: int  # 1 = per-period values, 252 = annualised

    def c(self, i, j):
        """c(i, j) = Cov(R_i, R_j)."""
        return self.C[i, j]

    def corr(self):
        """Correlation matrix."""
        d = np.sqrt(np.diag(self.C))
        return self.C / np.outer(d, d)

    def summary(self):
        return pd.DataFrame(
            {"mean_return": self.r, "variance": self.v2,
             "std_dev": np.sqrt(self.v2)}, index=self.tickers)

    def cov_df(self):
        return pd.DataFrame(self.C, index=self.tickers, columns=self.tickers)


def clean_returns(returns):
    """Drop rows with any missing value so all securities use the same dates
    (covariances need paired observations)."""
    df = pd.DataFrame(returns).apply(pd.to_numeric, errors="coerce")
    return df.replace([np.inf, -np.inf], np.nan).dropna(how="any")


def estimate(returns, periods_per_year=1, ddof=1):
    """Compute r, v^2 and the covariance matrix from a returns table.
    Keep ddof=1 (the unbiased N-1 estimator used in the text)."""
    df = clean_returns(returns)
    if df.shape[0] < 2:
        raise ValueError("Need at least 2 clean observations.")

    R = df.to_numpy(dtype=float)
    N, n = R.shape

    r = R.mean(axis=0)                 # sample means
    D = R - r                          # deviations from the means
    C = (D.T @ D) / (N - ddof)         # sample covariance matrix
    v2 = np.diag(C).copy()             # variances = diagonal of C

    # Optional annualisation (our own modelling choice: assumes i.i.d. returns)
    r, C, v2 = r * periods_per_year, C * periods_per_year, v2 * periods_per_year

    return Estimates(list(df.columns), r, v2, C, N, periods_per_year)


def check_positive_definite(C, tol=1e-12):
    """The optimiser needs C positive semi-definite. Returns smallest eigenvalue."""
    lam_min = np.linalg.eigvalsh(C).min()
    if lam_min < -tol:
        raise ValueError(f"Covariance matrix is not PSD (min eigenvalue {lam_min:.3e}).")
    return lam_min


# ============================================================================
# TASK 3 - CORE OPTIMISER (single b)
# ============================================================================
# maximize    E[W] - (b/2) Var(W)
# subject to  sum_i w_i = w   and   w_i >= 0
# with        E[W]   = w + sum_i w_i r_i
#             Var(W) = w_vec' C w_vec
# Equivalent convex QP:  minimize (b/2) w'Cw - r'w.

@dataclass
class OptimalPortfolio:
    tickers: list
    weights: np.ndarray    # amounts invested w_i (not proportions)
    b: float
    w_total: float
    E_W: float
    Var_W: float
    objective: float
    success: bool
    message: str
    active: np.ndarray     # True where w_i > tol

    def proportions(self):
        return self.weights / self.w_total

    def summary(self, tol=1e-8):
        return pd.DataFrame(
            {"amount": self.weights, "proportion": self.proportions(),
             "in_portfolio": self.weights > tol}, index=self.tickers)


def unconstrained_weights(est, b, w_total=1.0):
    """Closed-form solution ignoring w_i >= 0 (reference solution for Task 6).
    From the Lagrangian:  w = (1/b) C^-1 (r + lambda*1), lambda set so sum(w)=w_total."""
    n = len(est.r)
    C_inv = np.linalg.inv(est.C)
    ones = np.ones(n)
    A = ones @ C_inv @ ones
    B = ones @ C_inv @ est.r
    lam = (b * w_total - B) / A
    return (C_inv @ (est.r + lam * ones)) / b


def _objective_pieces(w_vec, est, w_total):
    E_W = w_total + est.r @ w_vec
    Var_W = w_vec @ est.C @ w_vec
    return E_W, Var_W


def optimize(est, b, w_total=1.0, x0=None, tol=1e-9, max_iter=500):
    """Solve the long-only mean-variance problem for a single b (SLSQP)."""
    if b <= 0:
        raise ValueError("b must be > 0 (risk-aversion parameter).")
    check_positive_definite(est.C)

    n = len(est.r)
    r, C = est.r, est.C

    def neg_objective(w_vec):
        E_W, Var_W = _objective_pieces(w_vec, est, w_total)
        return -(E_W - (b / 2) * Var_W)

    def neg_objective_grad(w_vec):
        return -r + b * (C @ w_vec)

    budget = LinearConstraint(np.ones((1, n)), w_total, w_total)  # sum(w) = w_total
    bounds = Bounds(lb=np.zeros(n), ub=np.full(n, np.inf))        # w_i >= 0

    if x0 is None:
        x0 = np.full(n, w_total / n)    # equal-weight start

    result = minimize(neg_objective, x0, jac=neg_objective_grad, method="SLSQP",
                      bounds=bounds, constraints=[budget],
                      options={"maxiter": max_iter, "ftol": tol})

    w_opt = np.clip(result.x, 0, None)              # remove tiny negative noise
    if w_opt.sum() > 0:
        w_opt = w_opt * (w_total / w_opt.sum())     # restore the budget

    E_W, Var_W = _objective_pieces(w_opt, est, w_total)
    return OptimalPortfolio(est.tickers, w_opt, b, w_total, E_W, Var_W,
                            E_W - (b / 2) * Var_W, result.success,
                            result.message, w_opt > 1e-8)


# ============================================================================
# TASK 4 - SENSITIVITY SWEEP & BREAKPOINTS
# ============================================================================

def sensitivity_sweep(est, b_values, w_total=1.0, verbose=True):
    """Run the optimiser for every b. The solution for the previous b is the
    warm start for the next one. Returns a DataFrame (rows = b, cols = assets)."""
    weights, x0 = [], None
    for b in b_values:
        result = optimize(est, b=b, w_total=w_total, x0=x0)
        if verbose and not result.success:
            print(f"Warning: optimizer did not converge for b = {b:.6g}")
        weights.append(result.weights)
        x0 = result.weights

    weights_df = pd.DataFrame(weights, columns=est.tickers, index=b_values)
    weights_df.index.name = "b"
    return weights_df


def detect_breakpoints(weights_df, tol=1e-8):
    """Detect approximate points where an asset enters or exits the portfolio."""
    active_df = weights_df > tol

    for ticker in weights_df.columns:
        changes = active_df[ticker].astype(int).diff()
        entered = weights_df.index[changes == 1]
        exited = weights_df.index[changes == -1]

        print(f"\n{ticker}")
        if len(entered) > 0:
            print("  Enters near b =", [f"{x:.4g}" for x in entered])
        else:
            print("  No entry detected")
        if len(exited) > 0:
            print("  Exits near b  =", [f"{x:.4g}" for x in exited])
        else:
            print("  No exit detected")


def plot_sensitivity(weights_df, filename="task4_sensitivity.png"):
    """Weights against the risk-aversion parameter b (log scale)."""
    plt.figure(figsize=(11, 7))
    for ticker in weights_df.columns:
        plt.plot(weights_df.index, weights_df[ticker], linewidth=2, label=ticker)
    plt.xscale("log")
    plt.xlabel("Risk-aversion parameter, b")
    plt.ylabel("Portfolio weight")
    plt.title("Sensitivity of Optimal Portfolio Weights to Risk Aversion")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()


# ============================================================================
# TASK 5 - MONTE CARLO BOOTSTRAP
# ============================================================================
# Idea: our estimates r and C come from ONE historical sample, so they contain
# estimation error. To see how much that error moves the weight-vs-b curves and
# the breakpoints, we:
#   1. resample the historical return rows WITH replacement (a "bootstrap
#      sample" of the same length N) - whole rows are drawn, so the
#      correlation between securities on the same day is preserved;
#   2. re-estimate r and C from that resampled data (Task 2);
#   3. re-run the whole sweep over b (Tasks 3-4);
#   4. repeat many times, then look at the spread of the weights and
#      breakpoints across replications.
# Assumption: daily returns are i.i.d. (the same one the textbook model makes).

def bootstrap_sweep(returns, b_values, n_boot=200, w_total=1.0,
                    periods_per_year=1, seed=42, progress_every=25):
    """Run n_boot bootstrap replications of the Task 4 sweep.

    Returns
    -------
    W : array, shape (n_boot, len(b_values), n_assets)  weights per replication
    tickers : list of security names
    """
    rng = np.random.default_rng(seed)
    clean = clean_returns(returns)
    R = clean.to_numpy(dtype=float)
    N = R.shape[0]
    tickers = list(clean.columns)

    W = np.full((n_boot, len(b_values), len(tickers)), np.nan)
    n_failed = 0

    for k in range(n_boot):
        idx = rng.integers(0, N, size=N)              # draw N row indices with replacement
        boot_df = pd.DataFrame(R[idx], columns=tickers)
        est_k = estimate(boot_df, periods_per_year=periods_per_year)

        try:
            sweep_k = sensitivity_sweep(est_k, b_values, w_total=w_total, verbose=False)
            W[k] = sweep_k.to_numpy()
        except ValueError:                            # e.g. covariance not PSD
            n_failed += 1

        if progress_every and (k + 1) % progress_every == 0:
            print(f"  bootstrap replication {k + 1}/{n_boot} done")

    if n_failed:
        print(f"  {n_failed} replication(s) skipped (numerical problems).")
    W = W[~np.isnan(W).any(axis=(1, 2))]
    return W, tickers


def summarise_bootstrap(W, tickers, b_values, original_sweep=None, lo=5, hi=95):
    """Mean, std and (lo, hi) percentile bands of each weight at each b, plus
    P(asset is in the portfolio | b)."""
    b_values = np.asarray(b_values)
    stats = {
        "mean": W.mean(axis=0),
        "std": W.std(axis=0, ddof=1),
        "lo": np.percentile(W, lo, axis=0),
        "hi": np.percentile(W, hi, axis=0),
        "p_active": (W > 1e-8).mean(axis=0),
    }
    stats["tickers"], stats["b"], stats["n_boot"] = tickers, b_values, W.shape[0]
    stats["original"] = original_sweep
    return stats


def bootstrap_breakpoints(W, tickers, b_values, tol=1e-8):
    """For every replication find, per asset, the first b where it ENTERS and
    the first b where it EXITS. Returns a summary table across replications."""
    b_values = np.asarray(b_values)
    rows = []
    for j, t in enumerate(tickers):
        entries, exits = [], []
        for k in range(W.shape[0]):
            active = (W[k, :, j] > tol).astype(int)
            d = np.diff(active)
            e_idx, x_idx = np.where(d == 1)[0], np.where(d == -1)[0]
            if len(e_idx): entries.append(b_values[e_idx[0] + 1])
            if len(x_idx): exits.append(b_values[x_idx[0] + 1])

        def q(v, p):
            return np.percentile(v, p) if len(v) else np.nan

        rows.append({
            "asset": t,
            "P(entry occurs)": len(entries) / W.shape[0],
            "entry b median": q(entries, 50),
            "entry b 5%": q(entries, 5), "entry b 95%": q(entries, 95),
            "P(exit occurs)": len(exits) / W.shape[0],
            "exit b median": q(exits, 50),
            "exit b 5%": q(exits, 5), "exit b 95%": q(exits, 95),
        })
    return pd.DataFrame(rows).set_index("asset")


def plot_bootstrap(stats, filename_bands="task5_bootstrap_bands.png",
                   filename_active="task5_prob_in_portfolio.png"):
    """(a) mean weight with a 5-95% band for each asset, original curve dashed;
       (b) probability that each asset is in the portfolio, against b."""
    tickers, b = stats["tickers"], stats["b"]
    n = len(tickers)

    fig, axes = plt.subplots(n, 1, figsize=(10, 2.6 * n), sharex=True)
    axes = np.atleast_1d(axes)
    for j, t in enumerate(tickers):
        ax = axes[j]
        ax.fill_between(b, stats["lo"][:, j], stats["hi"][:, j], alpha=0.3,
                        label="5-95% bootstrap band")
        ax.plot(b, stats["mean"][:, j], linewidth=2, label="bootstrap mean")
        if stats["original"] is not None:
            ax.plot(b, stats["original"][t].to_numpy(), "k--", linewidth=1.2,
                    label="original sample")
        ax.set_ylabel(f"{t}\nweight")
        ax.grid(True, which="both", alpha=0.3)
        if j == 0:
            ax.legend(loc="upper right", fontsize=8)
    axes[-1].set_xscale("log")
    axes[-1].set_xlabel("Risk-aversion parameter, b")
    fig.suptitle(f"Bootstrap robustness of weight-vs-b curves ({stats['n_boot']} resamples)")
    fig.tight_layout()
    fig.savefig(filename_bands, dpi=150)
    plt.show()

    plt.figure(figsize=(10, 6))
    for j, t in enumerate(tickers):
        plt.plot(b, stats["p_active"][:, j], linewidth=2, label=t)
    plt.xscale("log")
    plt.xlabel("Risk-aversion parameter, b")
    plt.ylabel("P(asset is in the portfolio)")
    plt.title("How often each asset is held across bootstrap resamples")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename_active, dpi=150)
    plt.show()


# ============================================================================
# TASK 6 - SEPARATION THEOREM VERIFICATION
# ============================================================================
# Separation theorem: when a risk-free asset is available, every investor holds
# the SAME risky portfolio (the tangency portfolio); risk aversion b only
# changes how much goes into it versus the risk-free asset.
#
# Why Task 3 cannot show this: it forces sum(w_i) = w_total, i.e. 100% in the
# risky assets, so as b changes the risky mix itself must change (it slides
# from "max return" at small b to "min variance" at large b).
#
# Model used here (risk-free rate rf per period):
#   W = w_total + rf*(w_total - sum w_i) + sum_i w_i R_i
#   maximise  E[W] - (b/2) Var(W)
#        =    const + mu'w - (b/2) w'Cw,     mu_i = r_i - rf  (excess return)
#   subject to  w_i >= 0  and  sum w_i <= w_total   (rest earns rf)
#
# Prediction (long-only): without the budget cap the problem is a cone, so
# w*(b) = w*(1)/b exactly -> all risky weights scale by 1/b, direction fixed.
# The cap only bites for b < b* = sum(w*(1)) / w_total. For b >= b* the
# direction is constant; for b < b* the portfolio is 100% risky and the mix drifts.

def optimize_with_rf(est, b, rf, w_total=1.0, x0=None, tol=1e-14, max_iter=1000):
    """Long-only mean-variance with a risk-free asset (SLSQP).
    The objective is rescaled to O(1) so SLSQP stays accurate at large b."""
    if b <= 0:
        raise ValueError("b must be > 0.")
    check_positive_definite(est.C)
    n = len(est.r)
    mu, C = est.r - rf, est.C
    k = b / max(float(mu @ np.linalg.solve(C, mu)), 1e-300)   # scale factor

    def f(w):
        return -k * (mu @ w - (b / 2) * (w @ C @ w))

    def g(w):
        return -k * (mu - b * (C @ w))

    cap = LinearConstraint(np.ones((1, n)), 0.0, w_total)        # 0 <= sum w <= w_total
    bounds = Bounds(np.zeros(n), np.full(n, np.inf))
    if x0 is None:
        x0 = np.full(n, 0.5 * w_total / n)
    res = minimize(f, x0, jac=g, method="SLSQP", bounds=bounds,
                   constraints=[cap], options={"maxiter": max_iter, "ftol": tol})
    w = np.clip(res.x, 0, None)
    return w, res.success


def separation_sweep(est, b_values, rf, w_total=1.0):
    """Solve for every b. Returns DataFrame: risky amounts, risky total,
    risk-free amount and the normalised risky mix (direction)."""
    rows, x0 = [], None
    for b in b_values:
        w, ok = optimize_with_rf(est, b, rf, w_total, x0=x0)
        if not ok:
            print(f"Warning: no convergence at b = {b:.6g}")
        x0 = w
        rows.append(w)
    W = np.array(rows)
    out = pd.DataFrame(W, columns=est.tickers, index=b_values)
    out.index.name = "b"
    out["risky_total"] = W.sum(axis=1)
    out["risk_free"] = w_total - W.sum(axis=1)
    return out


def verify_separation(est, b_values, rf, w_total=1.0, tol=1e-5):
    """Empirical test of the separation theorem. Returns a dict of results."""
    tick = est.tickers
    sw = separation_sweep(est, b_values, rf, w_total)
    W = sw[tick].to_numpy()
    s = sw["risky_total"].to_numpy()
    b = np.asarray(b_values)

    # Reference tangency direction from the cone problem (no budget cap), b = 1.
    # Solved independently of the sweep, so this is a real cross-check.
    w1, _ = optimize_with_rf(est, 1.0, rf, w_total=1e9)
    d_ref = w1 / w1.sum()
    b_star_pred = w1.sum() / w_total                    # predicted threshold

    # Closed form (valid if C^-1 mu >= 0, i.e. tangency portfolio is long-only)
    mu = est.r - rf
    z = np.linalg.solve(est.C, mu)
    d_closed = z / z.sum()
    closed_long_only = bool(np.all(z > 0))

    held = s > 1e-9
    cap_binds = s >= w_total * (1 - 1e-6)
    inside = held & ~cap_binds                          # region where theorem applies
    D = np.full_like(W, np.nan)
    D[held] = W[held] / s[held, None]                   # risky mix at each b

    dev = np.full(len(b), np.nan)
    dev[held] = np.abs(D[held] - d_ref).max(axis=1)     # max |weight-share error|
    cos = np.full(len(b), np.nan)
    cos[held] = (D[held] @ d_ref) / (np.linalg.norm(D[held], axis=1) * np.linalg.norm(d_ref))

    # Scaling law: b * w(b) should be constant where the cap is slack
    bw = W * b[:, None]
    scal_dev = (np.abs(bw[inside] - bw[inside][0]).max() / np.abs(bw[inside][0]).max()
                if inside.sum() > 1 else np.nan)

    b_star_obs = b[inside].min() if inside.any() else np.nan
    return {
        "sweep": sw, "direction": pd.DataFrame(D, columns=tick, index=b),
        "d_ref": pd.Series(d_ref, index=tick),
        "d_closed": pd.Series(d_closed, index=tick) if closed_long_only else None,
        "closed_long_only": closed_long_only,
        "dev": dev, "cos": cos, "inside": inside,
        "max_dev_inside": np.nanmax(dev[inside]) if inside.any() else np.nan,
        "min_cos_inside": np.nanmin(cos[inside]) if inside.any() else np.nan,
        "max_dev_outside": np.nanmax(dev[held & ~inside]) if (held & ~inside).any() else np.nan,
        "scaling_dev": scal_dev,
        "b_star_pred": b_star_pred, "b_star_obs": b_star_obs,
        "passed": bool(inside.any() and np.nanmax(dev[inside]) < tol),
        "tol": tol,
    }


def plot_separation(res, filename="task6_separation.png"):
    """(a) risky mix vs b: flat lines where theorem holds; (b) risky vs
    risk-free split: only this changes with b."""
    sw, D, b = res["sweep"], res["direction"], res["direction"].index.to_numpy()
    tick = list(D.columns)
    fig, ax = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
    for t in tick:
        ax[0].plot(b, D[t], linewidth=2, label=t)
    ax[0].axvline(res["b_star_pred"], color="k", ls=":", label="b* (budget cap stops binding)")
    ax[0].set_ylabel("share of risky portfolio")
    ax[0].set_title("Composition of the risky portfolio vs b (flat for b >= b*)")
    ax[0].legend(fontsize=8); ax[0].grid(True, which="both", alpha=0.3)
    w_total = sw["risky_total"].iloc[0] + sw["risk_free"].iloc[0]
    ax[1].plot(b, sw["risky_total"] / w_total, linewidth=2, label="risky assets")
    ax[1].plot(b, sw["risk_free"] / w_total, linewidth=2, label="risk-free asset")
    ax[1].axvline(res["b_star_pred"], color="k", ls=":")
    ax[1].set_ylabel("fraction of wealth"); ax[1].set_xlabel("Risk-aversion parameter, b")
    ax[1].set_title("Only the risky / risk-free split changes with b")
    ax[1].legend(); ax[1].grid(True, which="both", alpha=0.3)
    ax[1].set_xscale("log")
    fig.tight_layout(); fig.savefig(filename, dpi=150); plt.show()


def print_separation_report(res, est, weights_df_task4=None):
    print(f"\nTangency (risky) mix, independent cone solve:\n{res['d_ref'].round(6).to_string()}")
    if res["d_closed"] is not None:
        print(f"\nClosed form C^-1(r-rf)/1'C^-1(r-rf):\n{res['d_closed'].round(6).to_string()}")
        print("  max |numerical - closed form| =",
              f"{np.abs(res['d_ref'] - res['d_closed']).max():.2e}")
    else:
        print("\nClosed-form tangency has negative entries -> long-only tangency differs"
              " from the shorting-allowed one (expected; numerical cone solve is used).")
    print(f"\nPredicted threshold b* = {res['b_star_pred']:.4g}; "
          f"first observed grid b with slack budget = {res['b_star_obs']:.4g}")
    print(f"Grid points where theorem applies (b >= b*): {int(res['inside'].sum())} "
          f"of {len(res['inside'])}")
    print(f"Max |risky share - tangency share| for b >= b*: {res['max_dev_inside']:.2e}")
    print(f"Min cosine similarity to tangency direction for b >= b*: {res['min_cos_inside']:.10f}")
    print(f"Scaling law b*w(b) constant: max relative deviation = {res['scaling_dev']:.2e}")
    if not np.isnan(res["max_dev_outside"]):
        print(f"For b < b* (100% risky, cap binds) mix drifts by up to {res['max_dev_outside']:.3f}")
    if weights_df_task4 is not None:       # contrast with Task 4 (no risk-free asset)
        P = weights_df_task4.div(weights_df_task4.sum(axis=1), axis=0)
        print(f"Contrast, Task 4 (no risk-free asset): mix varies by up to "
              f"{(P.max() - P.min()).max():.3f} across b -> separation fails there.")
    print("\nRESULT:", "PASS - same risky portfolio for all b >= b*, only the risk-free split changes."
          if res["passed"] else f"FAIL - deviation exceeds tolerance {res['tol']:.0e}.")

# ============================================================================
# MAIN PROGRAM - runs Tasks 1 to 6 in order
# ============================================================================

if __name__ == "__main__":

    N_BOOT = 200                   # number of bootstrap resamples (Task 5)
    tickers = ["MTN.JO", "CPI.JO", "NPN.JO", "CML.JO", "SPP.JO"]

    # ---- TASK 1: data -------------------------------------------------------
    print("=" * 60, "\nTASK 1 - DATA\n" + "=" * 60)
    returns = get_returns(tickers, period="1y", interval="1d")
    print(returns.tail())

    # ---- TASK 2: estimation -------------------------------------------------
    print("\n" + "=" * 60, "\nTASK 2 - ESTIMATION\n" + "=" * 60)
    est = estimate(returns, periods_per_year=1)   # per-day estimates
    print(est.summary().round(6))
    print("\nCovariance matrix:\n", est.cov_df().round(6))
    print("\nCorrelation matrix:\n",
          pd.DataFrame(est.corr(), index=est.tickers, columns=est.tickers).round(2))
    print("\nMin eigenvalue of C:", check_positive_definite(est.C))
    print("N observations used:", est.n_obs)

    # ---- TASK 3: optimiser for a single b ----------------------------------
    print("\n" + "=" * 60, "\nTASK 3 - OPTIMISER (single b)\n" + "=" * 60)
    b = 0.005
    result = optimize(est, b=b, w_total=1.0)
    print(f"b = {b}  |  converged: {result.success} ({result.message})")
    print(result.summary().round(4))
    print(f"E[W] = {result.E_W:.6f}   Var(W) = {result.Var_W:.8f}   "
          f"Objective = {result.objective:.6f}")
    assert np.isclose(result.weights.sum(), 1.0, atol=1e-6), "Budget violated"
    assert np.all(result.weights >= -1e-8), "Long-only violated"
    print("\nUnconstrained weights (reference, may be negative):")
    print(pd.Series(unconstrained_weights(est, b=b), index=est.tickers).round(4))

    # ---- TASK 4: sensitivity sweep & breakpoints ---------------------------
    print("\n" + "=" * 60, "\nTASK 4 - SENSITIVITY SWEEP\n" + "=" * 60)
    b_values = np.logspace(-2, 3, 200)            # b = 0.01 ... 1000
    weights_df = sensitivity_sweep(est, b_values, w_total=1.0)
    plot_sensitivity(weights_df)

    print("\nApproximate entry/exit breakpoints:")
    detect_breakpoints(weights_df)

    selected_b = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000]
    rows = []
    for sb in selected_b:
        closest = b_values[np.argmin(np.abs(b_values - sb))]
        row = weights_df.loc[closest].copy()
        row["b"] = closest
        rows.append(row)
    selected_df = pd.DataFrame(rows)[["b"] + est.tickers]
    print("\nSelected risk-aversion values:")
    print(selected_df.to_string(index=False, float_format=lambda x: f"{x:.6f}"))

    # ---- TASK 5: Monte Carlo bootstrap -------------------------------------
    print("\n" + "=" * 60, "\nTASK 5 - MONTE CARLO BOOTSTRAP\n" + "=" * 60)
    b_boot = np.logspace(-2, 3, 60)               # coarser grid to keep it fast
    W, boot_tickers = bootstrap_sweep(returns, b_boot, n_boot=N_BOOT, seed=42)
    print(f"\nUsable bootstrap replications: {W.shape[0]}")

    original_on_boot_grid = sensitivity_sweep(est, b_boot, verbose=False)
    stats = summarise_bootstrap(W, boot_tickers, b_boot,
                                original_sweep=original_on_boot_grid)

    # Weight uncertainty at the selected b values
    print("\nBootstrap weights at selected b (mean, std, 5%-95%):")
    for sb in selected_b:
        i = int(np.argmin(np.abs(b_boot - sb)))
        print(f"\n  b = {b_boot[i]:.4g}")
        table = pd.DataFrame({
            "mean": stats["mean"][i], "std": stats["std"][i],
            "5%": stats["lo"][i], "95%": stats["hi"][i],
            "P(in portfolio)": stats["p_active"][i],
        }, index=boot_tickers)
        print(table.round(4).to_string())

    # Average spread across all b: a single "how fragile" number per asset
    print("\nMean bootstrap std of weight across all b (higher = less robust):")
    print(pd.Series(stats["std"].mean(axis=0), index=boot_tickers).round(4))

    # Breakpoint stability
    print("\nBreakpoint distribution across bootstrap resamples:")
    print(bootstrap_breakpoints(W, boot_tickers, b_boot).round(4).to_string())

    plot_bootstrap(stats)

    # ---- TASK 6: separation theorem ----------------------------------------
    print("\n" + "=" * 60, "\nTASK 6 - SEPARATION THEOREM\n" + "=" * 60)
    RF_ANNUAL = 0.07                              # assumption: set to a current SA T-bill / JIBAR rate
    rf = (1 + RF_ANNUAL) ** (1 / 252) - 1         # per-day rate, matches the daily estimates
    sep = verify_separation(est, b_values, rf, w_total=1.0)
    print_separation_report(sep, est, weights_df_task4=weights_df)
    plot_separation(sep)