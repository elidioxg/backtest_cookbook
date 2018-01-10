# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.analyzers as analyzer
import backtrader.indicators as btind
import datetime
import random
import pandas as pd
import itertools
from pandas import DataFrame

#### PARAMS
initial_cash = 1000000
comm = 0.002

#### TIME PARAMS
init_date = datetime.datetime(2017,1,1)
midle_date = datetime.datetime(2017,3,30)

end_buy_time = datetime.time(19,0,0)
time_to_sell  = datetime.time(21,30,0)
date_format = ('%Y-%m-%d') 
time_format = ('%H:%M:%S') 

#### FILE PARAMS
training_data = 'trainingdata.txt'
test_data = ['testdata.txt']
date_column  = 0
time_column  = 1
high_column  = 3
low_column   = 4
open_column  = 2
close_column = 5
volume_column = 6
interest_column=7

#### OPTIMIZATIONS PARAMS
## RSI RANGE
irfmin_min = 5
irfmin_max = 30
irfmax_min = 70
irfmax_max = 95
## RSI PERIOD RANGE
irfp_min = 2
irfp_max = 5
## BBANDS PERIOD RANGE
bollpmin = 5
bollpmax = 50
#### LOG
logging = 1 

class PercentCashSizer(bt.Sizer):
    params = {
            "percent":0.5
    }

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            price = data.close[0]
            shares = cash * self.p.percent
            volume = int(shares / price)
            return volume
        else:
            return self.broker.getposition(data).size

class stoptake(bt.Observer):
    # Observer for Stop Loss and Take Profit
    alias = ('STOPTAKE')
    lines = (
            'close',
            'ask',
            'stops',
            'takes', 
            )
    plotlines=dict(
              close = dict(color='black', linewidth=0.6),
              ask = dict(marker='*', markersize=5.),
              stops = dict(marker = 'v', markersize=5., color='red'),
              takes = dict(marker='^', markersize=5., color='green'),
              )
    plotinfo = dict(plot=True, subplot=True)

    def __init__(self):
        pass

    def next(self):
        self.lines.close[0] = self._owner.data.close[0]
        if self._owner.transaction:            
            if self._owner.sl is not None and self._owner.tp is not None:
                self.lines.ask[0] = self._owner.data.close[0]
                self.lines.stops[0] = self._owner.sl
                self.lines.takes[0] = self._owner.tp
                self._owner.transaction = False

class AcctValue(bt.Observer):
    '''
    This Observer was copied from ntguardian.wordpress.com
    https://ntguardian.wordpress.com/2017/06/19/walk-forward-analysis-demonstration-backtrader/
    '''
    alias = ("Value",)
    lines = ("value",)
    plotinfo = {
            "plot":True,
            "subplot":True
    }
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()

class AcctStats(bt.Analyzer):
    '''
    This Analyzer was copied from ntguardian.wordpress.com
    https://ntguardian.wordpress.com/2017/06/12/getting-started-with-backtrader/
    '''
    def __init__(self):
        self.start_val = self.strategy.broker.get_value()
        self.end_val = None
    def stop(self):
        self.end_val = self.strategy.broker.get_value()
    def get_analysis(self):
        return {"start": self.start_val, "end": self.end_val,
                "growth": self.end_val - self.start_val, "return": self.end_val / self.start_val}

class bollinger_irf(bt.Strategy):
    params = {
         #STRATEGY
        "irf_min":10,
        "irf_max":90,
        "irf_period":5,
        "boll_period":10,
        "boll_factor":2.,
         #STOPS
        "stoploss":0.006,
        "takeprofit":0.01,
         #OPTIMIZATION
        "optim":False,
        "optim_st":(10,90,5,10),
        "init_date":None,
         #TIME
        "buyfinaltime":datetime.time(18,0,0),
        "selltime":datetime.time(21,0,0),
         #LOG
        "logging":0
    }

    def __init__(self):
        self.order=None

        self.transaction = False # for Observer StopTake

        if self.params.optim:
            self.params.irf_min, self.params.irf_max, self.params.irf_period, self.params.boll_period = self.params.optim_st

        self.irf = btind.RSI_EMA(period=self.params.irf_period, lowerband=self.params.irf_min, upperband=self.params.irf_max)
        self.bollinger = btind.BBands(period=self.params.boll_period, devfactor=self.p.boll_factor )
        
        self.sl, self.tp = None, None

    def start(self):
        if self.p.logging >=1:
            print('[Strategy Start]')
            print('    IRF Period: %d    Low RSI: %d    High RSI: %d' % (self.p.irf_period, self.p.irf_min, self.p.irf_max))
            print('    Bollinger Period: %d    Factor: %.2f' % (self.p.boll_period, self.p.boll_factor))
            print('    Stop Loss: %.5f     Take Profit: %.5f' % (self.p.stoploss, self.p.takeprofit))
            print('    Initial Cash: %.5f\n' % self.broker.getcash())

    def next(self):
        if self.order:
            return
        dt = self.datas[0].datetime.datetime(0)
        t = self.datas[0].datetime.time(0)
        if self.params.init_date is not None:
            if dt < self.params.init_date:
                return
        if not self.position: 
           ##BUY CONDITIONS
            if t >= self.params.buyfinaltime:
                return
            if self.bollinger.lines.bot[0] > self.data.low[0]:
                if self.irf[0] <= self.params.irf_min:
                    self.order = self.buy()
                    self.transaction = True
                    if self.params.logging >=2:
                        self.log('BUY ORDER')
        else:
           ##SELL CONDITIONS
            if t >= self.params.selltime:
                self.order = self.sell()
                if self.params.logging >=2:
                    self.log('SELL ORDER: Time')
                return
            if self.irf[0] >= self.params.irf_max:
                self.order = self.sell()
                if self.params.logging >=2:
                    self.log('SELL ORDER: RSI') 
                return
            if self.bollinger.lines.top[0] <self.data.close[0]:
                self.order = self.sell()
                if self.params.logging >=2:
                    self.log('SELL ORDER: Top of BBands')
            if self.data.close[0] <= self.sl:
                self.order = self.sell()
                if self.params.logging >=2:
                    self.log('SELL ORDER: Stop Loss. Close: %.5f ' % self.data.close[0])
                return
            if self.data.close[0] >= self.tp:
                self.order = self.sell()
                if self.params.logging >=2:
                    self.log('SELL ORDER: Take Profit. Close: %.5f ' % self.data.close[0])

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print("%s    %s"  % (dt.isoformat(), txt))
 
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.sl = order.executed.price * (1 - self.p.stoploss)
                self.tp = order.executed.price * (1 + self.p.takeprofit)
                if self.params.logging >= 1:
                     self.log('<<<< Buy Executed: Price: %.2f, Cost: %.2f,  Commission: %.2f \n' % (order.executed.price, order.executed.value, order.executed.comm))
            else:
                self.sl, self.tp = None, None
                if self.params.logging >= 1:
                    self.log('>>>>> Sell Executed: Price: %.2f,  Cost: %.2f,  Commission: %.2f ' % (order.executed.price, order.executed.value, order.executed.comm))
            self.bar_executed = len(self)
        self.order = None

    def notify_trade(self,  trade):
        if not trade.isclosed:
            return
        if self.params.logging >=1:
            self.log('    Gross: %.5f   Net: %.5f \n' % (trade.pnl, trade.pnlcomm))

    def stop(self):
        if self.p.logging >= 1:
            print('Final Cash: %.2f ' % self.broker.getcash())
            print('___________________________________________________\n')

def training_window():
    boll_p = range(bollpmin, bollpmax)
    irf_p = range(irfp_min, irfp_max)
    irf_min= range(irfmin_min, irfmin_max)
    irf_max = range(irfmax_min, irfmax_max)
    return list(itertools.product(irf_min, irf_max, irf_p, boll_p))

def run(args=None):
    training = training_window()
    if logging >=1:
        print('Training data: %s' % training_data)
        print("Training size: %d iteractions" % len(list(training)))

    cerebro_train = bt.Cerebro(maxcpus=1)
    cerebro_train.broker.set_cash(initial_cash)
    cerebro_train.broker.setcommission(comm)
    cerebro_train.addanalyzer(AcctStats)
    cerebro_train.addsizer(PercentCashSizer)
    cerebro_train.optstrategy(bollinger_irf, optim=True, optim_st=training, logging=logging-1, buyfinaltime=end_buy_time, selltime=time_to_sell)
    
    data = bt.feeds.GenericCSVData(
        dataname = training_data,
        nullvalue = 0.,
        dtformat = date_format,
        tmformat = time_format,
        time = time_column,
        high = high_column,
        low = low_column,
        open = open_column,
        close = close_column,
        volume = volume_column,
        openinterest = interest_column,
        timeframe = bt.TimeFrame.Ticks
    ) 
    
    cerebro_train.adddata(data)

    res = cerebro_train.run()
    return_opt = DataFrame({r[0].params.optim_st: r[0].analyzers.acctstats.get_analysis() for r in res }).T.loc[:, ['end', 'growth', 'return']]
    sorted_opt = return_opt.sort_values("growth", ascending=False)
    print("\n__________________________________________________\n[Best results of train] \n %s " % sorted_opt)

    min_irf, max_irf, p_irf, p_boll = sorted_opt.iloc[0].name
    print('\n[Starting backtest of best result of train]\n')
    cerebro_view = bt.Cerebro()
    cerebro_view.broker.set_cash(initial_cash)
    cerebro_view.broker.setcommission(comm)
    cerebro_view.addobserver(stoptake)
    cerebro_view.addanalyzer(AcctStats)
    cerebro_view.addsizer(PercentCashSizer)
    cerebro_view.addstrategy(bollinger_irf, irf_min=min_irf,
            irf_max=max_irf, irf_period=p_irf, boll_period=p_boll, logging=logging, buyfinaltime=end_buy_time, selltime=time_to_sell)

    data = bt.feeds.GenericCSVData(
        dataname =  training_data,
        nullvalue=0.,
        dtformat=date_format,
        tmformat=time_format,
        time=time_column,
        high=high_column,
        low=low_column,
        open=open_column,
        close = close_column,
        volume= volume_column,
        openinterest=interest_column,
        timeframe=bt.TimeFrame.Ticks
    )

    cerebro_view.adddata(data)
    cerebro_view.addanalyzer(analyzer.DrawDown, _name='drawdown')
    cerebro_view.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)
    
    result = cerebro_view.run()
    dd = result[0].analyzers.drawdown.get_analysis()
    sr = result[0].analyzers.sharpe.get_analysis()
    if sr['sharperatio'] is None:
        sr_str = 0.
    else:
        sr_str = sr['sharperatio']
    retorno = 100. - (initial_cash/cerebro_view.broker.getvalue()*100.)
    print('\n[Result of best result of train]\nReturn: %.5f  \nDrawDown: %.2f  MoneyDown: %.2f  \nSharpe(Semanal): %.2f\n' % (retorno, dd['drawdown'], dd['moneydown'], sr_str))
    cerebro_view.plot(volume=False, stdstats=False, style='candles')

    print('\n_____________________________________________\n[Backtesting result on other datasets]')
    for i in test_data:

        cerebro_test = bt.Cerebro()
        cerebro_test.broker.set_cash(initial_cash)
        cerebro_test.broker.setcommission(comm)
        cerebro_test.addobserver(AcctValue)
        cerebro_test.addobserver(stoptake)
        cerebro_test.addanalyzer(AcctStats)
        cerebro_test.addsizer(PercentCashSizer)
        cerebro_test.addstrategy(bollinger_irf, irf_min=min_irf,
            irf_max=max_irf, irf_period=p_irf, boll_period=p_boll, init_date=midle_date, logging=logging, buyfinaltime=end_buy_time, selltime=time_to_sell)

        data = bt.feeds.GenericCSVData(
            dataname =  i,
            nullvalue=0.,
            dtformat=date_format,
            tmformat=time_format,
            time=time_column,
            high=high_column,
            low=low_column,
            open=open_column,
            close = close_column,
            volume= volume_column,
            openinterest=interest_column,
            timeframe=bt.TimeFrame.Ticks
        )

        cerebro_test.adddata(data)
        cerebro_test.addanalyzer(analyzer.DrawDown, _name='drawdown')
        cerebro_test.addanalyzer(analyzer.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Weeks)

        res = cerebro_test.run()
        dd_ = res[0].analyzers.drawdown.get_analysis()
        sr_ = res[0].analyzers.sharpe.get_analysis()
        retorno_ = 100. - (initial_cash/cerebro_test.broker.getvalue()*100.)
        if sr_['sharperatio'] is None: # Avoid error if there is none transactions 
            sr_str = 0.
        else:
            sr_str = sr_['sharperatio']
        print('\n[Result]: \nReturn: %.5f  \nDrawDown: %.2f  \nMoneyDown: %.2f\nSharpe Ratio(Semanal): %.2f' % (retorno_, dd_['drawdown'], dd_['moneydown'], sr_str))
        cerebro_test.plot(stdstats=False, volume=False, style='candles')

if __name__ == '__main__':
    run()
