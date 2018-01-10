# -*- coding: utf-8 -*-

from sklearn.preprocessing import StandardScaler
import sklearn.neural_network as classifier
import pandas as pd

class content:
    learn = None
    fn = 'memory.dat'
    fnsep = ','
    autoupdate = False

    def __init__(self, filename=fn, exists=False):
        self.fn = filename
        if exists:
            self.reopen()
        else:
            self.df = pd.DataFrame()
            self.df.to_csv(self.fn, sep=self.fnsep, index=False)

    def addresult(self, dataframe):
        self.df = self.df.append(dataframe)

    def saveas(self, filename, separator):
        self.df.to_csv(filename, sep=separator, index=False)

    def reopen(self):
        self.df = pd.read_csv(self.fn, sep=self.fnsep, header=0)#names= self.columns)

    def setautoupdate(value):
        self.autoupdate = value

    def getdata(self):
        return self.df

    def getfilename(self):
        return self.fn

    def update(self):
        self.df.to_csv(self.fn, sep=self.fnsep, index=False)

    def train(self, num_layers, results):
        self.learn = classifier.MLPClassifier(hidden_layer_sizes=(num_layers, num_layers, num_layers))
        scaler = StandardScaler()
        features = scaler.fit_transform(self.df) 
        self.learn.fit(features, results)

    def predict(self, current_features):
        if self.learn is not None:
            return self.learn.predict(current_features)[0]
        else:
            print("ERROR: Not Possible to Predict.")
            return 0

 
