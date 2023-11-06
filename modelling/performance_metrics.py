"""Tools for measuring portfolio performance"""

# External imports
import typing
import pandas


def annualized_performance_metrics(
    risk_free_rate: float, daily_return: pandas.DataFrame
) -> typing.Tuple[float, float, float]:
    """
    Computes portfolio performance metrics for a given risk-free rate and daily return series
    :param risk_free_rate: The annualized risk-free interest rate
    :param daily_return: A dataframe of daily returns to measure performance from
    :return: Annualized excess return, Sharpe ratio, and Sortino ratio
    """
    # Computing excess return
    risk_free_daily = (1 + risk_free_rate) ** (1 / 252) - 1
    excess_daily_return = daily_return - risk_free_daily

    # Annualized Excess Return
    annualized_excess_return = ((1 + excess_daily_return.mean()) ** 252) - 1

    # Sharpe Ratio
    sharpe_ratio = excess_daily_return.mean() / excess_daily_return.std()
    annualized_sharpe_ratio = (252**0.5) * sharpe_ratio

    # Sortino Ratio
    negative_excess_return = excess_daily_return.copy()
    negative_excess_return[negative_excess_return > 0] = 0
    sortino_ratio = excess_daily_return.mean() / negative_excess_return.std()
    annualized_sortino_ratio = (252**0.5) * sortino_ratio

    return annualized_excess_return, annualized_sharpe_ratio, annualized_sortino_ratio


def risk_free_range_performance_metrics(
    portfolio_value: pandas.DataFrame,
) -> typing.List[typing.List[float]]:
    """
    Computes portfolio performance metrics for a range of risk-free rates
    :param portfolio_value: A dataframe of daily portfolio valuations to measure performance from
    :return: Risk free rate, annualized excess return, Sharpe ratio, and Sortino ratio
    """
    daily_return: pandas.DataFrame = portfolio_value.pct_change().dropna()
    return [
        [percentage]
        + list(annualized_performance_metrics(percentage / 100, daily_return))
        for percentage in range(-1, 10)
    ]
