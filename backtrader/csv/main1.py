#-*-coding: utf-8 -*-

import backtrader as bt
import backtrader.feeds as btfeed
import backtrader.indicators as btind
import datetime
import argparse
import backtrader.analyzers as analyzer

#CONSTANTS
initial_cash = 100000.
commission = 0.001      #comission( 0.1%  =  0.001 )
lot_volume = 10

#FILE PARAMS
filename = 'aapl.us.txt'
date_column  = 0
time_column  = 1
high_column  = 3
low_column   = 4
open_column  = 2
close_column = 5
volume_column = 6
interest_column=7

#TIME PARAMS
init_date  = datetime.datetime(2017, 1, 1) # use to filter data 
final_date = datetime.datetime(2018, 1, 1) #   
date_format = ('%Y-%m-%d') 
time_format = ('%H:%M:%S') 

#STRATEGY PARAMS
slow_ma = 5 
fast_ma = 50
stoploss = .015
takeprofit = .02
buyfinaltime = datetime.time(19,0,0)
timetosell  = datetime.time(20,0,0)

#PLOTTING PARAMS
plot='true' #true or false
plotstyle='candle' ##bars, lines

#
scriptlog = 0 # 0(only final result), 1(operations), 2(all)

class SMA_ST(bt.SignalStrategy):

    def __init__(self, args):
        self.dataclose = self.datas[0].close
        self.order = None

        self.smafast, self.smaslow = btind.SMA(period=args.fastma), btind.SMA(period=args.slowma)
        self.stoploss = args.stoploss
        self.takeprofit = args.takeprofit
        self.sl, self.tp = None, None

        self.buyfinaltime = args.buyfinaltime
        self.timetosell = args.timetosell

        self.logging = args.log

    def next(self):
        tempo = self.datas[0].datetime.time(0)
        if self.order:
            return
        if not self.position:
            ##BUY CONDITIONS
            if tempo <= self.buyfinaltime:
                if self.smafast[0] > self.smaslow[0]:
                    if self.smafast[-1] < self.smaslow[-1]:
                        self.order = self.buy()
                        if self.logging >=2:
                            self.log('BUY ORDER\n  close: %.5f ' % self.dataclose[0])

        else:
            ##SELL CONDITIONS
            if tempo >= self.timetosell: 
                self.order = self.sell()
                if self.logging >= 2:
                    self.log('SELL ORDER: Time. \n  close: %.5f' % self.dataclose[0])
                return
            if self.smafast[0] < self.smaslow[0]:
                if self.smafast[-1] > self.smaslow[-1]:
                    self.order = self.sell()
                    if self.logging >=2:
                        self.log('SELL ORDER: Cross MA.\n  close: %.5f ' % self.dataclose[0])
                    return
            if self.dataclose[0] < self.sl:
                self.order = self.sell()
                if self.logging >=2:
                    self.log('SELL ORDER: Stoploss. \n  close: %.5f ' % self.dataclose[0])
                return
            if self.dataclose[0] > self.tp:       
                self.order = self.sell()
                if self.logging >=2:
                    self.log('SELL ORDER: Take Profit.\n  close: %.5f ' % self.dataclose[0])


    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print('%s    %s' % (dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            if order.isbuy():
                self.sl = order.executed.price * (1.0 - self.stoploss)
                self.tp = order.executed.price * (1.0 + self.takeprofit)
                if self.logging >=1:
                    self.log('<<<< BUY EXECUTED: Price: %.5f,  Cost: %.5f,  Commission: %.5f \nStop Loss: %.5f    Take Profit: %.5f' % (order.executed.price, order.executed.value, order.executed.comm, self.sl, self.tp))
            else:
                self.sl, self.tp = None, None
                if self.logging >=1:
                    self.log('>>>> SELL EXECUTED: Price: %.5f,  Cost: %.5f,  Commission: %.5f \n' % (order.executed.price, order.executed.value, order.executed.comm))
            self.bar_executed = len(self)

        self.order = None

    def notify_trade(self,  trade):
        if not trade.isclosed:
            return
        if self.logging >=1:
            self.log('  Gross: %.5f ,  Net: %.5f \n' % (trade.pnl, trade.pnlcomm))
    def start(self):
        pass
    def stop(self):
        pass

def parse_args(pargs=None):
    parser = argparse.ArgumentParser(
            description='Help' 
            )
    ##DATA ARGS
    parser.add_argument('--filename', '-a', required=False, default=filename,
            help='Filename of the feed.')
    
    parser.add_argument('--buyfinaltime', '-bft', required=False, default=buyfinaltime, type=datetime.time, help='Time limit to buy')
    parser.add_argument('--timetosell', '-tts', required=False, default=timetosell, type=datetime.time, help='Last time to hold position')

    ##STRATEGY ARGS
    parser.add_argument('--initial_cash', '-i', required=False, action='store',
            type=float, default=initial_cash, help='Initial cash')
    parser.add_argument('--lot_volume', '-lv', required=False, default=lot_volume, type=int, help='Lot volume')
    parser.add_argument('--commission', '-c', required=False, action='store', type=float, default=commission, help='Commission')
    parser.add_argument('--slowma', '-s',required=False, action='store',
            type=int, default=slow_ma, help='Período da média lenta')
    parser.add_argument('--fastma', '-f',required=False, action='store',
            type=int, default=fast_ma, help='Período da média rápida')
    parser.add_argument('--stoploss', '-sl', required=False, action='store', 
            type=float, default=stoploss, help='Stop Loss value')
    parser.add_argument('--takeprofit', '-sg', required=False, action='store', 
            type=float, default=takeprofit, help='Take Profit value')
 
    ##PLOT ARGS
    parser.add_argument('--plot', '-p', required=False, default=plot, action='store', help='True or False for plotting final result')
    parser.add_argument('--plotstyle', '-ps', required=False, default=plotstyle, help='Estilo da plotagem')
    parser.add_argument('--log', '-l', required=False, default=scriptlog,
            type=int, help='Níveis do log: 0, 1, 2')

    if pargs is not None:
        return parser.parse_args(pargs)
    return parser.parse_args()

def run(args=None):

    args = parse_args(args)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(args.initial_cash)
    cerebro.broker.setcommission(args.commission)
    if args.log >=1:
        print('Initial Cash: %.5f ' % cerebro.broker.getvalue())
        print('Commission: %.5f ' % (args.commission*100))
    
    #Create Data Feed
    data = btfeed.GenericCSVData(
        dataname = args.filename,
        fromdate = init_date,
        todate = final_date,
        nullvalue = 0.,
        dtformat = date_format,
        tmformat = time_format,
        datetime = date_column,
        time = time_column,
        high = high_column,
        low = low_column,
        open = open_column,
        close = close_column,
        volume = volume_column,
        openinterest = interest_column,
        timeframe=bt.TimeFrame.Ticks
            )

    cerebro.adddata(data)
    cerebro.addstrategy(SMA_ST, args)
    cerebro.addsizer(bt.sizers.SizerFix, stake=args.lot_volume)

    cerebro.addanalyzer(analyzer.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(analyzer.DrawDown, _name='drawdown')    
    cerebro.addanalyzer(analyzer.SharpeRatio, _name='sharpe',timeframe=bt.TimeFrame.Months)

    resultado = cerebro.run()

    res = resultado[0].analyzers.pyfolio.get_pf_items()
    dd = resultado[0].analyzers.drawdown.get_analysis()
    sr = resultado[0].analyzers.sharpe.get_analysis()

    if sr['sharperatio'] is None:
        sr_str = 0.
    else:
        sr_str = sr['sharperatio']

    retorno = 100. - (args.initial_cash/cerebro.broker.getvalue()*100.)
    print('\nReturn: %.5f  \nDrawDown: %.2f  \nSharpe Ratio: %.2f\n' % (retorno, dd['drawdown'], sr_str))
 
    argplot = str(args.plot).upper()
    if 'FALSE'.startswith(argplot):
        pass
    else:
        cerebro.plot(style=args.plotstyle)

if __name__ == '__main__':
    run()
    
