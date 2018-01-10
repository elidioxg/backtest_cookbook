# -*- coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeed
import backtrader.indicators as btind
import pandas as pd
import datetime
import argparse

from volume_sizer import PercentCashSizer
import memory

## STRATEGY PARAMS ##
initial_cash = 10000.
commission = 0.00
stoploss = 0.02
takeprofit = 0.02
## INDICATOR ##
rsi_period = 5

## TIME CONSTANTS ##
init_date = datetime.datetime(2010, 1, 1) # use to filter data
final_date = datetime.datetime(2018, 1, 1)
date_format = ('%Y.%m.%d')
time_format = ('%H:%M')

## FILE CONSTANTS ##
#inputdata = "dol5m_train.csv"
inputdata = "dol5m_backtest.csv"
rsi_memory_file = "rsi_.dat"
results_memory_file = "results_.dat"
update = False ## Update Memory

## INPUT FILE CONSTANTS ##
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
        "stoploss": 0.015,
        "takeprofit":0.035,
    }

    def start(self):
        print("[Initializing Memories]")
        self.memory_rsi = memory.content(filename=self.memory_file, exists=False)
        self.memory_results = memory.content(filename=self.results_file, exists=False)
        print("[Initializing Strategy]")
        print("        Stop Loss: %.3f" % self.p.stoploss)
        print("        Take Profit: %.3f" % self.p.takeprofit)
        print("        RSI Period: %d" % self.p.rsi_period)
        print("        RSI memory file: %s" % self.memory_rsi.getfilename())
        print("        Results memory file: %s" % self.memory_results.getfilename())

    def stop(self):
        print("[Stoping Strategy]")
        if self.update:
            print("[Saving Memories]")
            self.memory_rsi.update()
            self.memory_results.update()

    def __init__(self, args):
        print("[Loading strategy]")
        self.update = args.update_memory
        self.memory_file = args.memory_rsi
        self.results_file = args.memory_results

        ## Updating params with input args ##
        self.p.stoploss, self.p.takeprofit = args.stoploss, args.takeprofit
        self.p.rsi_period = args.rsi_period

        ## Indicator Data ##
        self.rsi = btind.RSI_EMA(period=self.p.rsi_period)

        self.order = None
        self.tp, self.sl = None, None

        self.i = 0 # increment to avoid empty data

    def next(self):
        self.i+=1
        if self.i < 5:
            return
        if self.order:
            return
        if not self.position:
            self.order = self.buy()
            self.tp = self.datas[0].close[0] * (1 + self.p.takeprofit)
            self.sl = self.datas[0].close[0] * (1 - self.p.stoploss)
            self.training_data = pd.DataFrame({
                "rsi1":self.rsi[0],
                "rsi2":self.rsi[-1],
                "rsi3":self.rsi[-2],
                "rsi4":self.rsi[-3],
                "rsi5":self.rsi[-4],
            }, [0])
        else:
            if self.datas[0].close[0] >= self.tp:
                self.order = self.sell()
                result = pd.DataFrame({"result":1}, [0])
                if self.update:
                    self.memory_rsi.addresult(self.training_data)
                    self.memory_results.addresult(result)
                return
            if self.datas[0].close[0] <= self.sl:
                self.order = self.sell()
                result = pd.DataFrame({"result":-1}, [0])
                if self.update:
                    self.memory_rsi.addresult(self.training_data)
                    self.memory_results.addresult(result)

    def log(self,  txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print("[%s]        %s " % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.log("    <<<< Buy Executed\n        Price: %.2f\n        Cost: %.2f\n        Commission: %.2f" % (order.executed.price, order.executed.value, order.executed.comm))
            else:
                self.tp, self.sl = None, None
                self.log("    >>>> Sell Executed\n        Price: %.2f\n        Cost: %.2f\n        Commission: %.2f" % (order.executed.price, order.executed.value, order.executed.comm))
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
        ##  STRATEGY PROPERTIES  ##
        "rsi_period": 5,
        "stoploss": 0.015,
        "takeprofit":0.035,
        "feature_window":10,
    }

    def start(self):
        print("[Strategy Start]")
        print("        Stop Loss: %.3f" % self.p.stoploss)
        print("        Take Profit: %.3f" % self.p.takeprofit)
        print("        RSI Period: %d" % self.p.rsi_period)
 
    def stop(self):
        print("[Strategy Stop]")
        if self.update:
            self.memory_rsi.update()
            self.memory_results.update()

    def __init__(self, args):
        print("[Loading strategy]")

        ## Memory Params ##
        self.memory_file = args.memory_rsi
        self.results_file = args.memory_results
        self.update = args.update_memory 
        self.memory_rsi = memory.content(filename=self.memory_file, exists=True)
        self.memory_results = memory.content(filename=self.results_file, exists=True)

        self.memory_rsi.train(num_layers=5, results=self.memory_results.getdata().filter(["result"], axis=1))

        self.p.stoploss, self.p.takeprofit = args.stoploss, args.takeprofit
        
        ## Indicators Data ##
        self.rsi = btind.RSI_EMA(period=self.p.rsi_period)

        self.tp, self.sl = None, None
        self.order = None

        self.i = 0

    def next(self):
        self.i+=1
        if self.i < 5:
            return
        if self.order:
            return
        if not self.position:
            self.features = pd.DataFrame({
                "rsi1":self.rsi[0],
                "rsi2":self.rsi[-1],
                "rsi3":self.rsi[-2],
                "rsi4":self.rsi[-3],
                "rsi5":self.rsi[-4]
            }, [0])
            if self.memory_rsi.predict(self.features) > 0:
                self.order = self.buy()
                self.tp = self.datas[0].close[0] * (1 + self.p.takeprofit)
                self.sl = self.datas[0].close[0] * (1 - self.p.stoploss)
            else:
                pass
        
        else:
            if self.datas[0].close[0] >= self.tp:
                self.order = self.sell()
                result = pd.DataFrame({"result":1}, [0])
                if self.update:
                    self.memory_rsi.addresult(self.features)
                    self.memory_results.addresult(result)
                return
            if self.datas[0].close[0] <= self.sl:
                self.order = self.sell()
                result = pd.DataFrame({"result":-1}, [0])
                if self.update:
                    self.memory_rsi.addresult(self.features)
                    self.memory_results.addresult(result)

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
    parser.add_argument('--input_data', '-id', required=False, default=inputdata, type=str, help='')
    parser.add_argument('--initial_cash', '-ic', required=False, default=initial_cash, type=float, help="")
    parser.add_argument('--commission', '-c', required=False, default=commission, type=float, help="")
    parser.add_argument('--memory_rsi', '-mem1', required=False, default=rsi_memory_file, type=str, help='')
    parser.add_argument('--memory_results', '-mem2', required=False, default=results_memory_file, type=str, help='')
    parser.add_argument('--update_memory', '-um', required=False, default=update, type=bool, help='')
    parser.add_argument('--rsi_period', '-rp', required=False, default=rsi_period, type=int, help='')
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
        print("    BACKTESTING Strategy")
    elif args.mode == 2:
        cerebro.addstrategy(training, args)
        print("    TRAIN Strategy")
    cerebro.broker.setcash(args.initial_cash)
    cerebro.broker.setcommission(args.commission)
    print("    Initial money: %.2f" % cerebro.broker.getcash())
    print("    Comission: %.5f" % args.commission)
    data = btfeed.GenericCSVData(
            dataname = args.input_data,
            fromdata = init_date,
            todate = final_date,
            nullvalue = 0.,
            dtformat = date_format,
            tmformat = time_format,
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
