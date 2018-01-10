#  -*- coding: utf-8 -*-

import backtrader as bt

class PercentCashSizer(bt.Sizer):

    params = {
         "percent":0.5
    } 

    def _getsizing(self, comminfo, cash, data, isbuy):

        if isbuy:
            price = data.close[0]
            shares = cash * self.p.percent
            volume = int(shares/price)
            return volume
        else:
            return self.broker.getposition(data).size
