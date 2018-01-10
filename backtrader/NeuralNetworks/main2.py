# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeed
import backtrader.indicators as btind
import pandas as pd
import datetime
import argparse

from volume_sizer import PercentCashSizer
import memory

## CONSTANTES DE ESTRATÉGIA ##
initial_cash = 10000.
commission = 0.00
lot_volume = 1000

stoploss = 0.02
takeprofit = 0.02

## PARÂMETROS DE INDICADORES ##
bollinger_period = 10
bollinger_factor = 2
rsi_period = 5
ema_period = 5
fast_period = 7
slow_period = 50
atr_period = 10
sar_period = 2
sar_step = 0.02
sar_max = 0.2

## CONSTANTES DE TEMPO ##
init_date = datetime.datetime(2010, 1, 1)
final_date = datetime.datetime(2018, 1, 1)
date_format = ('%Y.%m.%d')
time_format = ('%H:%M')

## CONSTANTES DE ARQUIVO ##
#inputdata = "dol5m_train.csv"
inputdata = "dol5m_backtest.csv"
update = False ## update do arquivo de memoria 

## CONSTANTES DE ARQUIVO DE INPUT ##
column_date = 0
column_time = 1
column_open = 2
column_high = 3
column_low = 4
column_close = 5
column_volume = 6
column_interest = 7

## MODE = 2   Train 
## MODE = 1   Backtesting 
MODE = 2

class training(bt.SignalStrategy):
    params = {
        ##  STRATEGY PARAMS  ##
        "rsi_period": 5,
        "ema_period": 5,
        "fast_period": 7,
        "slow_period": 50,
        "sar_period":2,
        "sar_step":0.02,
        "sar_max":0.2,
        "stoploss": 0.015,
        "takeprofit":0.035,
        "feature_window":10,
    }

    def start(self):
        print("[Strategy Start]")
        print("        Stop Loss: %.3f" % self.p.stoploss)
        print("        Take Profit: %.3f" % self.p.takeprofit)
        print("        Feature Window Size: %d" % self.p.feature_window)
        print("        RSI Period: %d" % self.p.rsi_period)
        print("        Fast MA Period: %d" % self.p.fast_period)
        print("        Slow MA Period: %d" % self.p.slow_period)
        print("        Parabolic SAR:  Period %d  Step %.2f Step Max %.2f" % (self.p.sar_period, self.p.sar_step, self.p.sar_max))
        print("[Creating Memories]")
        self.mem_close = memory.content(filename="close.dat", exists=False)
        self.mem_rsi = memory.content(filename="rsi.dat", exists=False)
        self.mem_fast = memory.content(filename="fast.dat", exists=False)
        self.mem_slow = memory.content(filename="slow.dat", exists=False)
        self.mem_sar = memory.content(filename="sar.dat", exists=False)
        self.mem_results = memory.content(filename="results.dat", exists=False)

    def stop(self):
        print("[Strategy Finished]")
        if self.update:
            print("[Updating Memories]")
            self.mem_close.update()
            self.mem_rsi.update()
            self.mem_fast.update()
            self.mem_slow.update()
            self.mem_sar.update()
            self.mem_results.update()

    def __init__(self, args):
        print("[Loading strategy]")
        self.update = args.update_memory

        ## Updating params with input args ##
        self.p.stoploss, self.p.takeprofit = args.stoploss, args.takeprofit
        self.p.rsi_period = args.rsi_period
        self.p.ema_period = args.ema_period
        self.p.fast_period = args.fast_period
        self.p.slow_period = args.slow_period
        self.p.atr_period = args.atr_period

        ## Indicators Data ##
        self.rsi = btind.RSI_EMA(period=self.p.rsi_period)
        self.ema  = btind.EMA(period=self.p.ema_period)
        self.fast = btind.SMA(period=self.p.fast_period)
        self.slow = btind.SMA(period=self.p.slow_period)
        self.sar = btind.PSAR(period=self.p.sar_period, af=self.p.sar_step, afmax=self.p.sar_max)

        self.order = None
        self.tp, self.sl = None, None

        self.data_name = 'AIBot'

        self._close = []
        self._rsi = []
        self._fast = []
        self._slow = []
        self._sar = []

        self.inc = 0

    def next(self):
        self.inc +=1
        if self.inc <= self.p.feature_window:
            return
        if self.order:
            return
        if not self.position:
            self.order = self.buy()
            self.tp = self.datas[0].close[0] * (1 + self.p.takeprofit)
            self.sl = self.datas[0].close[0] * (1 - self.p.stoploss)
            for i in range(0, -self.p.feature_window-1,-1):
                self._close.append(self.datas[0].close[i-1]-self.datas[0].close[i])
                self._rsi.append(self.rsi[i])
                self._fast.append(self.fast[i]-self.datas[0].close[i])
                self._slow.append(self.slow[i]-self.datas[0].close[i])
                self._sar.append(self.sar[i]-self.datas[0].close[i])
        else:
            if self.datas[0].close[0] >= self.tp:
                self.order = self.sell()
                _result = [1]
                if self.update:
                    self.mem_results.addresult(pd.DataFrame(_result, columns=[0]))
                    self.mem_close.addresult(pd.DataFrame({x:self._close[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_rsi.addresult(pd.DataFrame({x:self._rsi[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_fast.addresult(pd.DataFrame({x:self._fast[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_slow.addresult(pd.DataFrame({x:self._slow[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_sar.addresult(pd.DataFrame({x:self._sar[x] for x in range(0, self.p.feature_window)}, [0]))

                self._close = []
                self._rsi = []
                self._fast = []
                self._slow = []
                self._sar = []
                return
            if self.datas[0].close[0] <= self.sl:
                self.order = self.sell()
                _result = [-1]
                if self.update:
                    self.mem_results.addresult(pd.DataFrame(_result, columns=[0]))
                    self.mem_close.addresult(pd.DataFrame({x:self._close[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_rsi.addresult(pd.DataFrame({x:self._rsi[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_fast.addresult(pd.DataFrame({x:self._fast[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_slow.addresult(pd.DataFrame({x:self._slow[x] for x in range(0, self.p.feature_window)}, [0]))
                    self.mem_sar.addresult(pd.DataFrame({x:self._sar[x] for x in range(0, self.p.feature_window)}, [0]))
                self._close = []
                self._rsi = []
                self._fast = []
                self._slow = []
                self._sar = []


    def log(self,  txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print("[%s]        %s " % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log("    <<<< Buy Executed\n        Price: %.3f\n        Cost: %.3f\n        Commission: %.5f" % (order.executed.price, order.executed.value, order.executed.comm))
            else:
                self.tp, self.sl = None, None
                self.log("    >>>> Sell Executed\n        Price: %.3f\n        Cost: %.3f\n        Commission: %.5f" % (order.executed.price, order.executed.value, order.executed.comm))
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        if trade.pnl >= 0:
            self.log("            ++++ Gross: %.5f   Net: %.5f" % (trade.pnl, trade.pnlcomm))
        else:         
            self.log("            ---- Gross: %.5f   Net: %.5f" % (trade.pnl, trade.pnlcomm))


class backtesting(bt.SignalStrategy):
 
    params = {
        ##  STRATEGY PARAMS  ##
        "rsi_period": 5,
        "ema_period": 5,
        "fast_period": 7,
        "slow_period": 50,
        "sar_period":2,
        "sar_step":0.02,
        "sar_max":0.2,

        "stoploss": 0.015,
        "takeprofit":0.035,
        "feature_window":10,
    }

    def start(self):
        print("[Strategy Starting]")
        print("        Stop Loss: %.3f" % self.p.stoploss)
        print("        Take Profit: %.3f" % self.p.takeprofit)
        print("        Feature Window: %d" % self.p.feature_window)
        print("        RSI Period: %d" % self.p.rsi_period)
        print("        EMA Period: %d" % self.p.ema_period)
        print("        Fast MA Period: %d" % self.p.fast_period)
        print("        Slow MA Period: %d" % self.p.slow_period)
        print("        Parabolic SAR:  Period %d  Step %.2f Step Max %.2f\n" % (self.p.sar_period, self.p.sar_step, self.p.sar_max))
 
    def stop(self):
        print("[Strategy Finished]")
        if self.update:
            self.mem_close.update()
            self.mem_rsi.update()
            self.mem_fast.update()
            self.mem_slow.update()
            self.mem_sar.update()
            self.mem_results.update()

    def __init__(self, args):
        print("[Loading strategy]")

        ## Memory Params ##
        self.update = args.update_memory 
        self.mem_close = memory.content(filename="close.dat", exists=True)
        self.mem_rsi = memory.content(filename="rsi.dat", exists=True)
        self.mem_fast = memory.content(filename="fast.dat", exists=True)
        self.mem_slow = memory.content(filename="slow.dat", exists=True)
        self.mem_sar = memory.content(filename="sar.dat", exists=True)
        self.mem_results = memory.content(filename="results.dat", exists=True)

        res = self.mem_results.getdata()

        self.mem_close.train(num_layers=self.p.feature_window,results=res)
        self.mem_rsi.train(num_layers=self.p.feature_window, results=res)
        self.mem_fast.train(num_layers=self.p.feature_window, results=res)
        self.mem_slow.train(num_layers=self.p.feature_window, results=res)
        self.mem_sar.train(num_layers=self.p.feature_window, results=res)

        self.p.stoploss, self.p.takeprofit = args.stoploss, args.takeprofit
        
        ## Indicators Data ##
        self.rsi = btind.RSI_EMA(period=self.p.rsi_period)
        self.ema  = btind.EMA(period=self.p.ema_period)
        self.fast = btind.SMA(period=self.p.fast_period)
        self.slow = btind.SMA(period=self.p.slow_period)
        self.sar = btind.PSAR(period=self.p.sar_period, af=self.p.sar_step, afmax=self.p.sar_max)

        self.tp, self.sl = None, None
        self.order = None

        self.inc=0

    def next(self):
        self.inc+=1
        if self.inc < self.p.feature_window:
            return
        if self.order:
            return
        _close = []
        _rsi = []
        _fast = []
        _slow = []
        _sar = []
        if not self.position:
            for i in range(0, -self.p.feature_window,-1):
                _close.append(self.datas[0].close[i-1]-self.datas[0].close[i])
                _rsi.append(self.rsi[i])
                _fast.append(self.fast[i]-self.datas[0].close[i])
                _slow.append(self.slow[i]-self.datas[0].close[i])
                _sar.append(self.sar[i]-self.datas[0].close[i])
            p1 = self.mem_close.predict(_close)
            p2 = self.mem_rsi.predict(_rsi)
            p3 = self.mem_fast.predict(_fast)
            p4 = self.mem_slow.predict(_slow)
            p5 = self.mem_sar.predict(_sar)

            if collections.Counter([p1,p2,p3,p4,p5]).most_common(1)[0][1] >=3:
                self.order = self.buy()
                self.tp = self.datas[0].close[0] * (1 + self.p.takeprofit)
                self.sl = self.datas[0].close[0] * (1 - self.p.stoploss)
            else:
                pass
        
        else:
            if self.datas[0].close[0] >= self.tp:
                self.order = self.sell()
                return
            if self.datas[0].close[0] <= self.sl:
                self.order = self.sell()

    def log(self,  txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print("[%s]        %s " % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log("    <<<< Buy Executed\n        Price: %.3f\n        Cost: %.3f\n        Commission: %.5f" % (order.executed.price, order.executed.value, order.executed.comm))
            else:
                self.tp, self.sl = None, None
                self.log("    >>>> Sell Executed\n        Price: %.3f\n        Cost: %.3f\n        Commission: %.5f" % (order.executed.price, order.executed.value, order.executed.comm))
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        if trade.pnl >= 0:
            self.log("            ++++ Gross: %.5f   Net: %.5f" % (trade.pnl, trade.pnlcomm))
        else:         
            self.log("            ---- Gross: %.5f   Net: %.5f" % (trade.pnl, trade.pnlcomm))


def parse_args(pargs=None):
    parser = argparse.ArgumentParser(description="Help")
    parser.add_argument('--mode', '-m', required=False, default=MODE, type=int, help="")
    parser.add_argument('--initial_cash', '-ic', required=False, default=initial_cash, type=float, help="")
    parser.add_argument('--commission', '-c', required=False, default=commission, type=float, help="")
    parser.add_argument('--input_data', '-id', required=False, default=inputdata, type=str, help='')
    parser.add_argument('--update_memory', '-um', required=False, default=update, type=bool, help='')
    parser.add_argument('--rsi_period', '-rp', required=False, default=rsi_period, type=int, help='')
    parser.add_argument('--ema_period', '-ep', required=False, default=ema_period, type=int, help='')
    parser.add_argument('--fast_period', '-fp', required=False, default=fast_period, type=int, help='')
    parser.add_argument('--slow_period', '-sp', required=False, default=slow_period, type=int, help='')
    parser.add_argument('--atr_period', '-ap', required=False, default=atr_period, type=int, help='')
    parser.add_argument('--sar_period', '-psp', required=False, default=sar_period, type=int, help='')
    parser.add_argument('--sar_step', '-pss', required=False, default=sar_step, type=float, help='')
    parser.add_argument('--sar_max', '-psm', required=False, default=sar_max, type=float, help='')

    parser.add_argument('--stoploss', '-sl', required=False, default=stoploss, type=float, help='')
    parser.add_argument('--takeprofit', '-tp', required=False, default=takeprofit, type=float, help='')

    if pargs is not None:
        return parser.parse_args(pargs)
    return parser.parse_args()

def run(args=None):
    args = parse_args(args)
    print("[Initializing Cerebro]")
    cerebro = bt.Cerebro()
    if args.mode == 1:
        cerebro.addstrategy(backtesting, args)
        print("    Strategy added: BACKTESTING")
    elif args.mode == 2:
        cerebro.addstrategy(training, args)
        print("    Strategy added: TRAIN")
    cerebro.broker.setcash(args.initial_cash)
    print("    Initial money: %.2f" % cerebro.broker.getcash())
    cerebro.broker.setcommission(args.commission)
    print("    Comission: %.5f" % args.commission)
    data = btfeed.GenericCSVData(
            dataname = args.input_data,
            fromdata = init_date,
            todate = final_date,
            nullvalue = 0.,
            dtformat = date_format,
            tmformat = time_format,
            #datetime = column_datetime,
            time = column_time,
            high = column_high,
            low = column_low,
            open = column_open,
            close = column_close,
            volume = column_volume,
            openinterest = column_interest,
            timeframe = bt.TimeFrame.Ticks
        )
    cerebro.adddata(data)
    print("    Data file: %s" % args.input_data)

    cerebro.addsizer(PercentCashSizer)
 
    print("[Starting Cerebro]")
    result = cerebro.run() 
    print("\n    Final Value: %.2f" % cerebro.broker.getvalue())
    if args.mode <=1:
        print("[Plotting]")
        cerebro.plot(plotstyle='candle')

if __name__ == '__main__':
    run()
