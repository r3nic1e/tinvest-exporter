from datetime import datetime, timedelta

from prometheus_client.core import CollectorRegistry, Gauge, Info
from tinvest import SyncClient


class TinvestCollector(object):
    account_id: str
    client: SyncClient
    registry: CollectorRegistry = CollectorRegistry()

    position_average_price: Gauge = Gauge("position_average_price", "Average position price",
                                          labelnames=["name", "currency"], registry=registry)
    position_average_price_no_nkd: Gauge = Gauge("position_average_price_no_nkd",
                                                 "Average position price",
                                                 labelnames=["name", "currency"], registry=registry)
    position_last_price: Gauge = Gauge("position_last_price", "Position last price",
                                       labelnames=["name"], registry=registry)
    position_close_price: Gauge = Gauge("position_close_price", "Position close price",
                                        labelnames=["name"], registry=registry)
    position_expected_yield: Gauge = Gauge("position_expected_yield", "Expected yield",
                                           labelnames=["name", "currency"], registry=registry)
    position_balance: Gauge = Gauge("position_balance", "Balance", labelnames=["name"], registry=registry)
    position_info: Info = Info("position", "Position information", labelnames=["name"], registry=registry)
    position_lots: Gauge = Gauge("position_lots", "Lots count", labelnames=["name"], registry=registry)

    currency_balance: Gauge = Gauge("currency_balance", "Currency balance", labelnames=["name"], registry=registry)

    etf_info: Info = Info("etf", "ETF information", labelnames=["name"], registry=registry)
    etf_last_price: Gauge = Gauge("etf_last_price", "ETF last price", labelnames=["name"], registry=registry)

    operation_commission: Gauge = Gauge("operation_commission", "Operations commission",
                                        labelnames=["figi", "currency", "instrument_type", "operation_type"],
                                        registry=registry)
    operation_broker_commission: Gauge = Gauge("operation_broker_commission", "Broker commission",
                                               labelnames=["figi", "currency", "instrument_type"], registry=registry)
    operation_coupon: Gauge = Gauge("operation_coupon", "Coupon payments sum",
                                    labelnames=["figi", "currency", "instrument_type"], registry=registry)
    operation_dividend: Gauge = Gauge("operation_dividend", "Dividend payments sum",
                                      labelnames=["figi", "currency", "instrument_type"], registry=registry)

    def __init__(self, token: str, account_id: str):
        self.client = SyncClient(token, use_sandbox=False)
        self.account_id = account_id

    def collect(self):
        self.generate_positions_metrics()
        self.generate_currencies_metrics()
        self.generate_etfs_metrics()
        self.generate_operations_metrics()

        for metric in self.registry.collect():
            yield metric

    def generate_positions_metrics(self):
        for position in self.__get_positions():
            if position.average_position_price_no_nkd is not None:
                self.position_average_price_no_nkd.labels(position.name,
                                                          position.average_position_price_no_nkd.currency.name). \
                    set(position.average_position_price_no_nkd.value)
                currency = position.average_position_price_no_nkd.currency.name
            else:
                self.position_average_price.labels(
                    position.name, position.average_position_price.currency.name). \
                    set(position.average_position_price.value)
                currency = position.average_position_price.currency.name

            self.position_expected_yield.labels(position.name, position.expected_yield.currency.name). \
                set(position.expected_yield.value)

            self.position_balance.labels(position.name).set(position.balance)

            orders = self.client.get_market_orderbook(position.figi, 0)
            self.position_last_price.labels(position.name).set(orders.payload.last_price)
            self.position_close_price.labels(position.name).set(orders.payload.close_price)

            self.position_info.labels(position.name).info({
                "currency": currency,
                "blocked": position.blocked or "0",
                "figi": position.figi,
                "instrument_type": position.instrument_type,
                "isin": position.isin or "",
                "ticker": position.ticker,
            })
            self.position_lots.labels(position.name).set(position.lots)

    def generate_currencies_metrics(self):
        for currency in self.__get_currencies():
            self.currency_balance.labels(currency.currency.name).set(currency.balance)

    def generate_etfs_metrics(self):
        for etf in self.__get_etfs():
            orders = self.client.get_market_orderbook(etf.figi, 0)
            self.etf_last_price.labels(etf.name).set(orders.payload.last_price)

            self.etf_info.labels(etf.name).info({
                "currency": etf.currency.name,
                "figi": etf.figi,
                "isin": etf.isin,
                "ticker": etf.ticker,
                "trade_status": orders.payload.trade_status.name,
            })

    def generate_operations_metrics(self):
        for operation in self.__get_operations():
            if operation.commission is not None:
                self.operation_commission.labels(operation.figi, operation.commission.currency.name,
                                                 operation.instrument_type.name, operation.operation_type.name). \
                    inc(float(operation.commission.value))

            if operation.operation_type.name == 'broker_commission':
                self.operation_broker_commission.labels(operation.figi, operation.currency.name,
                                                        operation.instrument_type.name). \
                    inc(float(operation.payment))
            elif operation.operation_type.name == 'coupon':
                self.operation_coupon.labels(operation.figi, operation.currency.name, operation.instrument_type.name). \
                    inc(float(operation.payment))
            elif operation.operation_type.name == 'dividend':
                self.operation_dividend.labels(operation.figi, operation.currency.name,
                                               operation.instrument_type.name). \
                    inc(float(operation.payment))

    def __get_positions(self):
        portfolio = self.client.get_portfolio(self.account_id)
        return portfolio.payload.positions

    def __get_currencies(self):
        currencies = self.client.get_portfolio_currencies(self.account_id)
        return currencies.payload.currencies

    def __get_etfs(self):
        etfs = self.client.get_market_etfs()
        return etfs.payload.instruments

    def __get_operations(self):
        operations = self.client.get_operations(
            datetime.now() - timedelta(minutes=1),
            datetime.now(),
            broker_account_id=self.account_id
        )
        return operations.payload.operations
