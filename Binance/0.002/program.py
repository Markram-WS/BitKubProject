import time
import requests 
import hmac
import json
import hashlib
import numpy as np
from datetime import datetime
import pandas as pd
import json
import os
import threading
import csv
#----------
import configparser
###############################################################################################
#-----------------------------------------FTX API---------------------------------------------#
###############################################################################################
import time
import hmac
from typing import Optional, Dict, Any, List
from requests import Request, Session, Response

class ftxAPI():
    def __init__(self,host,key,secret):
        self._api_host = host
        self._api_key = key
        self._api_secret  = secret
        self.ts = int(time.time() * 1000)
        self._subaccount_name = ""
        self._session = Session()
        
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)
    
    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, params=params)
    
    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._api_host + path, **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request) -> None:
        self.ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{self.ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self._api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(self.ts)
        if self._subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self._subaccount_name)
    
    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                raise Exception(data['error'])
            return data['result']
    
    
    def get_ticker(self,market_name):
        return self._get(f'/markets/{market_name}/orderbook?depth={1}')
    '''
        def place_orders(self,market,side,size,price,type_ord):
            return self._post(f'/orders',{   'market': market,
                                             'side': side,
                                             'price': price,
                                             'size': size,
                                             'type': type_ord,
                                         })
    '''

    
    def place_conditional_orders(self,market,side,size,type_ord,open_price,tp):
        return self._post(f'/conditional_orders',{    'market': market, 
                                                      'side': side,
                                                      'size': size,
                                                      'type': type_ord,
                                                      'triggerPrice':tp,
                                                      'orderPrice':open_price
                                                 })
    
    def historicalPrice(self,market_name,resolution,limit,start_time,end_time):
        return self._get(f'/markets/{market_name}/candles?resolution={resolution}&limit={limit}&start_time={start_time}&end_time={end_time}')
    
    def get_open_orders(self,market):
        return self._get(f'/orders?market={market}')
    
    def place_orders(self,market,side,size,price,type_ord):
        tm = time.localtime() # get struct_time
        time_string = time.strftime("%Y-%m-%d, %H:%M:%S", tm)
        tr = self.get_ticker(market)
        if(side == 'buy'):
            price = tr['asks'][0][0]
        else:
            price = tr['bids'][0][0]
            
        return {"createdAt": time_string,
                "filledSize": 0,
                "future": market,
                "id": int(time.time()),
                "market": market,
                "price": price,
                "remainingSize": size,
                "side": side,
                "size": size,
                "status": "open",
                "type": type_ord,
              }
    
    def get_open_conditional_order(self,market):
        return self._get(f'/conditional_orders?market={market}')
    
    def get_conditional_order(self,conditional_order_id):
        return self._get(f'/conditional_orders/{conditional_order_id}/triggers')





############################################################################################
#------------------------------------  symbol class   -------------------------------------#
############################################################################################
class symbol():
    def __init__(self,sym,API):
        self.symbol = sym
        self.ticker = {'ask':'','bid':'','askv':'','bidv':''}
        self.his_price={}
        self.API = API
        
    def get_ticker(self):
        try:
            ticker = self.API.get_ticker(self.symbol)
            self.ticker['bid'] = float(ticker['bids'][0][0])
            self.ticker['bidv'] = float(ticker['bids'][0][1])
            self.ticker['ask'] = float(ticker['asks'][0][0])
            self.ticker['askv'] = float(ticker['asks'][0][1])
            return True
        except:
            return False
        
    def getHisPrice(self,tf,nbar):
        price = self.API.historicalPrice(self.symbol,tf,nbar,int(time.time())-(tf*nbar),int(time.time()))
        self.his_price = pd.DataFrame.from_dict(price)     
        
    def ma(self,type_bar):
        return self.his_price[type_bar].mean()

    def refBar(self,type_bar,bar):
        return self.his_price[type_bar][len(self.his_price)-bar]
    
    def atr(self):
        tr=[]
        for i in range(len(self.his_price)):
            tr.append(
                max(
                    (self.his_price['high'][i]-self.his_price['low'][i]),
                    abs(self.his_price['high'][i]-self.his_price['close'][i]),
                    (self.his_price['low'][i]-self.his_price['close'][i])
                )) 
        return np.mean(tr)





###################################################################################
#---------------------------------  main program  --------------------------------#
###################################################################################
class main():
    def __init__(self):
        #self.API = bitkubAPI(API_HOST,API_KEY,API_SECRET)
        config = configparser.ConfigParser()
        config.read('config.ini') 
        
        #API
        self.API = ftxAPI(
            config['API']['host'],
            config['API']['key'].encode(),
            config['API']['secret']
        )
        self.api_connect = True
        
        #system
        self.margin = float(config['SYSTEM']['margin'])
        self.size = float(config['SYSTEM']['size'])
        self.fee = float(config['SYSTEM']['fee'])
        self.side = config['SYSTEM']['side'].split(',')
        self.symbol = config['SYSTEM']['symbol'].split(',')
        self.order = {}
        self.ticker = {}
        self.zone = 0
        self.system = True
        
        #indecator 
        self.timeframe = int(config['SYSTEM']['timeframe']) #min #day:1440  #5m:5
        self.period = int(config['SYSTEM']['period']) #bar

        #time
        self.tm = time.localtime() # get struct_time
        self.time_string = time.strftime("%Y-%m-%d, %H:%M:%S", self.tm)
        self.refSec = 0
        self.timeout = 0
        
        #HisPrice init
        self.sys = list([])
        for i in range(len(self.symbol)):self.sys.append(i)
        for i in range(len(self.sys)): 
            self.sys[i] = symbol(self.symbol[i],self.API)
        self.hisPrice_init()
            
    ########################### write data ###########################          
    def write_log(self,dict_order): 
        csv_columns=[]
        for i in dict_order.keys():
            csv_columns.append(i)
        if(os.path.isfile('log.csv') == False):
            with open('log.csv', 'w', newline='') as csv_object: 
                writer = csv.DictWriter(csv_object, fieldnames=csv_columns)
                writer.writeheader()
                writer.writerow(dict_order) 
        else:
            with open('log.csv', 'a', newline='') as csv_object: 
                writer = csv.DictWriter(csv_object, fieldnames=csv_columns)
                writer.writerow(dict_order)   
            
    def load_order (self):
        if(os.path.isfile('data.json') == True):
            with open('data.json') as infile:
                self.order = json.load(infile)   
            
    def save_order(self): 
        with open('data.json', 'w') as outfile: 
            json.dump(self.order, outfile)

    ########################### order #############################
    def cal_size(self,price):
        return  round(self.size/price,1)

    ########################### getdata ###########################   
    def time_check(self):
        #get_time
        self.tm = time.localtime() # get struct_time
        self.time_string = time.strftime("%Y-%m-%d, %H:%M:%S", self.tm)
        return True
    
    def hisPrice_init(self):
        for i in range(len(self.sys)):
            self.sys[i].getHisPrice(self.timeframe * 60,200)
        for i in range(len(self.sys)):
            if i == 0: 
                self.ma = self.sys[i].ma('close')
                self.refBar = self.sys[i].refBar('high',1)
            elif i == 1: 
                self.ma = round(self.ma - self.sys[i].ma('close') , 5)
                self.refBar = round(self.refBar - self.sys[i].refBar('high',1) , 5)
            else:
                print('getHisPrice function error')
        
    def getHisPrice(self):
        if(self.refSec != self.tm and self.tm.tm_sec % self.timeframe  == 0):
            self.refSec = self.tm.tm_sec
            hisdatas = list()
            for i in range(len(self.sys)):
                get_hisdata = threading.Thread(target=self.sys[i].getHisPrice, args=[self.timeframe*60, self.period])
                get_hisdata.start()
                hisdatas.append(get_hisdata)
            for i in hisdatas:
                i.join()
                
            for i in range(len(self.sys)):
                if i == 0: 
                    self.ma = self.sys[i].ma('close')
                    self.refBar = self.sys[i].refBar('high',1)
                elif i == 1: 
                    self.ma = round(self.ma - self.sys[i].ma('close') , 5)
                    self.refBar = round(self.refBar - self.sys[i].refBar('high',1) , 5)
                else:
                    print('getHisPrice function error')
    
    ########################### open order ###########################             
    def place_orders_open(self,sym,side,size,price):
        res = self.API.place_orders(sym,side,size,price,'market')
        return{ 'status':'open',
                'open_id' : res['id'],
                'open_date': res['createdAt'],
                'open_price': res['price'],
                'side':side,
                'size': res['size'],
                'sl': '',
                'tp': '',
                'fee':round( (res['size']*res['price'])*self.fee ,5),
                'order_comment':'',
                }

                        
    #-----long order-----side[i]           
    def long_open_conditon(self):
        #------check short_conditon
        long_conditon = all([  self.ticker['ask'] <= self.ma,
                               abs(self.ticker['ask'] - self.zone) < self.margin/100,
                               str(self.zone) not in self.order.keys()
                          ])
        
        if(self.time_check() and long_conditon):
            dict_order=list([])
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[i] == 'buy' else self.sys[i].ticker['bid']
                dict_order.append(self.place_orders_open(self.sys[i].symbol,self.side[i],self.cal_size(price),price))
                
            print(f' ----------------------------------- open long {self.zone} ----------------------------------- ')
            self.order[f'{self.zone}'] = {}
            for i in range(len(self.sys)):
                self.order[f'{self.zone}'][self.sys[i].symbol] = dict_order[i]
                print(dict_order[i])
            self.save_order()
            print('')
            
    #-----short order-----side[-i]            
    def short_open_conditon(self):
        #------check short_conditon
        short_conditon = all([    self.ticker['ask'] >= self.ma,
                               abs(self.ticker['ask'] - self.zone) < self.margin/100,
                               str(self.zone) not in self.order.keys()
                          ])

        if(self.time_check() and short_conditon):
            dict_order=list([])
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[-i] == 'buy' else self.sys[i].ticker['bid']
                dict_order.append(self.place_orders_open(self.sys[i].symbol,self.side[-i],self.cal_size(price),price))
                                  
            print(f' ----------------------------------- open short {self.zone} ----------------------------------- ')
            self.order[f'{self.zone}'] = {}
            for i in range(len(self.sys)):
                self.order[f'{self.zone}'][self.sys[i].symbol] = dict_order[i]
                print(dict_order[i])
            self.save_order()
            print('')

            
    ########################### close_order ###########################       
    #-----place orders------
    def place_orders_close(self,sym,side,size,price,zone,comment):
        res = self.API.place_orders(sym,side,size,price,'market')
        self.order[f'{zone}'][sym]['status'] = 'close'
        self.order[f'{zone}'][sym]['close_id'] = res["id"]
        self.order[f'{zone}'][sym]['close_date'] = res["createdAt"]
        self.order[f'{zone}'][sym]['close_price'] = res["price"]
        close_val = res["price"]*self.order[f'{zone}'][sym]['size']                                 #USDT
        open_val = self.order[f'{zone}'][sym]['size'] * self.order[f'{zone}'][sym]['open_price']    #USDT
        self.order[f'{zone}'][sym]['fee'] = self.order[f'{zone}'][sym]['fee'] + (close_val * self.fee)
        
        #calculate order_profit
        if(self.order[f'{zone}'][sym]['side']=='buy'):
            self.order[f'{zone}'][sym]['order_profit'] = close_val - open_val - self.order[f'{zone}'][sym]['fee'] 
        elif(self.order[f'{zone}'][sym]['side']=='sell'):
            self.order[f'{zone}'][sym]['order_profit'] = open_val - close_val - self.order[f'{zone}'][sym]['fee'] 
        else:
            print('error calculate order_profit')
            print('')
            self.system = False
            
        
        self.order[f'{zone}'][sym]['order_comment'] = f'close {comment}'
        self.order[f'{zone}'][sym]['zone'] = zone
        return self.order[f'{zone}'][sym]
        
    #-----process close_order---------
    #-----CLOSE LONG
    def process_closeOrder(self,zone):
        zone = float(zone)
        if(self.order[f'{zone}'][self.sys[0].symbol]['side'] == 'buy'
          and self.ticker['bid'] >= zone + self.margin):                      
            dict_order=list([])
            zProfit = 0                      
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[-i] == 'buy' else self.sys[i].ticker['bid']
                dict_order.append(self.place_orders_close(self.sys[i].symbol,self.side[-i],self.order[f'{zone}'][self.sys[i].symbol]['size'],price,zone,price))
                #cal zProfit
                zProfit = zProfit + dict_order[i]['order_profit']
            print(f' ----------------------------------- close long order ----------------------------------- ')
            for i in range(len(self.sys)):
                dict_order[i]['zone_profit']=zProfit
                self.write_log(dict_order[i])
                print(dict_order[i])
            #SAVE LOG
            del self.order[f'{zone}']
            self.save_order()
            print('')
            
        #-----CLOSE SHORT
        elif(self.order[f'{zone}'][self.sys[0].symbol]['side'] == 'sell' 
           and self.ticker['ask'] <= zone - self.margin):
            for i in range(len(self.sys)):
                price = self.sys[i].ticker['ask'] if self.side[i] == 'buy' else self.sys[i].ticker['bid']
                dict_order.append(self.place_orders_close(self.sys[i].symbol,self.side[i],self.order[f'{zone}'][self.sys[i].symbol]['size'],price,zone,price))
                #cal zProfit
                zProfit = zProfit + dict_order[i]['order_profit'] 
            print(f' ----------------------------------- close short order ----------------------------------- ')
            for i in range(len(self.sys)):
                dict_order[i]['zone_profit']=zProfit
                self.write_log(dict_order[i])
                print(dict_order[i])
            del self.order[f'{zone}']
            self.save_order()
            print('')
            
    #-----operation------
    def close_order(self):
        processes = list()
        for zone in self.order.keys():
            process = threading.Thread(target=self.process_closeOrder, args=[zone])
            process.start()
            processes.append(process)
        for process in processes:
            process.join()
            
    ######################## program control ####################
    def controlPanel(self,timeout):
        self.timeout  = timeout*60 #min to sec
        lastsec=0
        while(self.system and (timeout != 0)):
            if(lastsec != self.tm.tm_sec):
                lastsec = self.tm.tm_sec
                self.timeout -= 1
            if(self.timeout<0):
                self.system = False
                
    ########################### start ###########################   
    def start(self):
        #try:

        try:
            #get_ticker
            self.api_connect = all([self.sys[i].get_ticker() for i in range(len(self.sys))])

            #cal_ticker
            self.ticker['ask']  = round(self.sys[0].ticker['ask'] - self.sys[1].ticker['bid'], 5)
            self.ticker['bid']  = round(self.sys[0].ticker['bid'] - self.sys[1].ticker['ask'], 5)

            #----thread set 
            thr_getHisPrice = threading.Thread(target=self.getHisPrice)
            #----thread start 
            thr_getHisPrice.start()
        except:
            self.api_connect=False


        if(self.api_connect):
            #cal zone
            self.zone = round((self.ticker['ask'] // self.margin) * self.margin,5)
            
            #----thread set 
            #------open long condition ------
            thr_open_long = threading.Thread(target=self.long_open_conditon)
            #------check short_conditon
            thr_open_short = threading.Thread(target=self.short_open_conditon)
               
            #----thread start 
            thr_open_long.start()
            thr_open_short.start()
            #----thread join 
            thr_open_long.join()
            thr_open_short.join()
            
            #------check close_conditon
            self.close_order()
            
            ask  = self.ticker['ask']
            print(f'{self.sys[0].symbol}/{self.sys[1].symbol} zone:{self.zone} ask:{ask} ma:{self.ma} {self.time_string}  timeout:{self.timeout}  ',end='\r')
        else:           
            print(f'connection failed {self.time_string}                                                                                          ',end='\r')
            

program = main()
program.load_order()

while(program.system):
    program.start()
    time.sleep(0)