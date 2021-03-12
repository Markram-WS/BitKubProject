import requests
import json

import winsound

import numpy as np
from mongoDB import database
import settrade.openapi 
import time 
from os import path
import pandas as pd

#------------------------------

class CSTsystem():
    def __init__(self):
        # general parameter
        self.localTime = time.localtime()
        self.serverTime ={}
        self.system = False
        self.test = False
        self.alert = False
        
        #settrade API
        self.settrade_api = False
        self.account_no="wasanCAF-D"
        self.app_id='UWfc7cUnu0VTrjNv'
        self.app_secret='GBxqS6A11vWu0lkv9fCmn7stq4cj3Zch8dnsUnred/g='
        self.broker_id = 'SANDBOX'
        self.app_code='SANDBOX'
        self.is_auto_queue = False
        self.pincode = "000000"
        #---
        self.invester = ''
        self.deriAccount = ''
            
        #--Database
        self.clearOrder =  False
        self.database = database(
            database='trading_db'
            ,collection= 'CSTsys1'
            ,mongodb_srv="mongodb+srv://wasan:1234@cluster0.ujivx.gcp.mongodb.net/trading_db?retryWrites=true&w=majority"
            ,line_token='QHQPbxDrgD35meR5LDh0PniRVDGYUBNrH8ls42ThiKM')
        
        # trading parameter
        self.orders = []
        self.indecator = {}
        self.zone = []
        # --symbol
        self.symbol ={ 'symbol':'S50H21M21',
                        'margin':0,
                        'vol':1,
                        'maxVol':5,
                        'muntiply':200,
                        'leverage':0.1,
                        'zone':{'min':1,'max':20,'range':0.5},
                        'detail':{"sym1":"S50H21","sym2":"S50M21"}
                     }
        
    #APIserver
    def getTicker(self):
        res=requests.get('http://localhost:8000/market/ticker').json()
        if(res['response'] == False):
            print(f"resCode:{res['resCode']} message:{res['message']}")
        return res
                      
    def getServerDate(self):
        res=requests.get('http://localhost:8000/market/date').json()
        if(res['response'] == False):
            print(f"resCode:{res['resCode']} message:{res['message']}")
        return res
                      
    def getServerTime(self):
        res=requests.get('http://localhost:8000/market/time').json()
        if(res['response'] == False):
            print(f"resCode:{res['resCode']} message:{res['message']}")
        return res
        
    def getMarketStatus(self):
        res=requests.get('http://localhost:8000/market/status/Equity').json()  
        return res
    
    def getHisData(self,sym):
        res=requests.get(f'http://localhost:8000/loadHisData/{sym}').json()  
        if(res['response'] == False):
            print(f"resCode:{res['resCode']} message:{res['message']}")
        return res
    
    #-----------------------------------------
    def genZone(self):
        zone = np.arange(self.symbol['zone']['min'],self.symbol['zone']['max'],self.symbol['zone']['range']) 
        for j in range(len(zone)):
            zone[j]=round(zone[j],2)
        self.symbol['zone']=zone
                       
    #--------------database-----------------
    #load database
    def loadDatabase(self): 
        print("--download database")
        self.orders = self.database.load({'order_status':'open'})
        
    #del database    
    def delOpenOrder(self): 
        orders = self.database.load({'order_status':'open'})
        for i in range(len(self.orders)):
            self.database.clear({'_id':orders[i]['_id']})
        self.orders = []
        print("--delete open order")            
        
    #del database    
    def delAllOrder(self): 
        orders = self.database.load({})
        for i in range(len(orders)):
            self.database.clear({'_id':orders[i]['_id']})
        orders = []
        print("--delete all order")  
    
    #-----------------------------------------------#
    ###############| indecator |################
    #-----------------------------------------------#
    
    def movingAverage(self,period):
        sym1df = pd.read_csv(f"data/{cst.symbol['detail']['sym1']}.csv") 
        sym2df = pd.read_csv(f"data/{cst.symbol['detail']['sym2']}.csv") 
        return (sym2df['Close'][:period] - sym1df['Close'][:period]).mean()
    
    #-----------------------------------------------#
    ###############| initialization |################
    #-----------------------------------------------#
    
    def initialization(self): 
        self.genZone()
        #------------settrade_api-------------
        #set Obj
        if(self.settrade_api == True):
            # settradeAPI
            self.invester = settrade.openapi.Investor( self.app_id,
                                                        self.app_secret,
                                                        self.broker_id,
                                                        self.app_code,
                                                        self.is_auto_queue)
            self.deriAccount = self.invester.Derivatives(self.account_no)
        else:
            self.invester = ""
            self.deriAccount = ""
            
        #--------------load Database--------------
        self.loadDatabase()       
        if(self.clearOrder==True):
            self.delAllOrder() 

        #set _system
        self._system = True
        
        #setup
        #get hisdata
        #self.getHisData(self.symbol['detail']['sym1'])
        #self.getHisData(self.symbol['detail']['sym2'])

        #cal indicator 
        self.indecator['ma'] = cst.movingAverage(3)
        print('========initialization========')
        
    #-----------------------------------------------#
    ##############| unity function |################
    #-----------------------------------------------#
    def placeOrder(self,symbol,price,volume,side,position): 
        order={}
        if(self.settrade_api==True): 
            resPlaceOrder = deriAccount.place_order(symbol,price,volume,side,position,self.pincode)
            if(resPlaceOrder['success']==True):
                resGetOrder = deriAccount.get_order(resPlaceOrder["data"])
                print("PlaceOrder success")
                print("")
                return {'success':True,'Data':
                           {
                               'orderNo':resGetOrder['order_no'],
                               'entry':f"{resGetOrder['entry_date']} {resPlaceOrder['entry_time']}",
                               'price':resGetOrder['price'],
                               'qty':resGetOrder['qty'],
                               'side':resGetOrder['side'],
                               'symbol':resGetOrder['symbol'],
                               'status':resGetOrder['show_status'],
                               'reject_code':resGetOrder['reject_code'],
                               'reject_reason':resGetOrder['reject_reason'],
                           }
                       }
            else:
                print(f"Error,{resPlaceOrder['status_code']}:{resPlaceOrder['message']}")
                return {'success':False}
        else:
            tm = time.strftime("%d/%m/%Y %H:%M:%S", self.localTime )
            return {'success':True,
                    'Data':
                       {
                           'orderNo':f'{len(self.orders)}{int(abs(price)*100)}',
                           'entry':f"{tm}",
                           'price':price,
                           'qty':volume,
                           'side':side,
                           'symbol':symbol,
                           'status':"MP",
                           'reject_code':0,
                           'reject_reason':"",
                       }
                    }
                
        
    def MKTtime(self):
        tm_d_open_morning =  (self.localTime.tm_wday !=  6) and (self.localTime.tm_wday !=  5)
        tm_h_open_morning   = self.localTime.tm_hour > 9 
        tm_m_open_morning   = self.localTime.tm_hour == 9   and self.localTime.tm_min >= 45
        tm_h_close_morning  = self.localTime.tm_hour < 12
        tm_m_close_morning  = self.localTime.tm_hour == 12  and self.localTime.tm_min <= 30


        tm_d_open_afternoon =  (self.localTime.tm_wday !=  6) and (self.localTime.tm_wday !=  5)
        tm_h_open_afternoon =  self.localTime.tm_hour > 14
        tm_m_open_afternoon =  self.localTime.tm_hour == 14   and self.localTime.tm_min >= 15
        tm_h_close_afternoon = self.localTime.tm_hour < 16
        tm_m_close_afternoon = self.localTime.tm_hour == 16   and self.localTime.tm_min <= 55

        #Check Mkt
        if(self.test==False):
            time_condition = ( (tm_d_open_morning
                                and (tm_h_open_morning or tm_m_open_morning)
                                and (tm_h_close_morning or tm_m_close_morning) ) 
                            or (tm_d_open_afternoon
                                and (tm_h_open_afternoon or tm_m_open_afternoon))
                                and (tm_h_close_afternoon or tm_m_close_afternoon) 
                             )

            #check SYSTEM server
            if(self.system == False):
                #mkt check
                if(time_condition):
                    if(self.getMarketStatus()['response']):
                        self.system = True
                    else:
                        self.system = False
            
            if(self.system == True):
                if(time_condition == False):
                    self.system = False

        #Test
        elif(self.test == True):
            self.system = True
            
        return self.system
    
    
    def sendMsg(self,order):
        sym  =order['symbol']
        price=order['price']
        vol  =order['qty']
        side =order['side']
        orderStatus=order['order_status']
        
        if(orderStatus=='open'):
            msg=[f"{orderStatus} {sym}", f"{side} {vol} @ {price}"]
        if(orderStatus=='close'):
            profit =order['profit']
            msg=[f"{orderStatus} {sym}", f"{side} {vol} @ {price} Profit:{round(profit,3)}"]
            
        self.database.lineMsg(f"{msg[0]}\r\n {msg[1]}")
    
    
    #----------------------------------------------------------------------------#
    #################\ main \##################
    #----------------------------------------------------------------------------#
    def main(self): 
        self.localTime = time.localtime()
        tmFormat = time.strftime("%Y-%m-%d %H:%M:%S", self.localTime )
        
        #check market time 
        
        if(self.MKTtime()):

            ticker = self.getTicker()
            
            if(ticker['response']):
   
                ASK  =  ticker['data'][self.symbol['symbol']]['ask']
                ASKv =  ticker['data'][self.symbol['symbol']]['volAsk']
                BID  =  ticker['data'][self.symbol['symbol']]['bid']
                BIDv =  ticker['data'][self.symbol['symbol']]['volBid']

                ma = self.indecator['ma'] 
                ordersend={}
                resOrder={}
                checkEquity = True
                #--------------------------------close order----------------------------------
                if(len(self.orders) > 0):
                    for i in range(len(self.orders)):
                        if(self.orders[i]['side']=='LONG' 
                        and BID >= self.orders[i]['price'] + self.symbol['margin']):
                            ordersend = {'symbol': self.symbol['symbol'],
                                 'side':'SHORT',
                                 'price':BID,
                                 'vol':self.symbol['vol'],
                                 'order_status':'close',
                                 'list_del':i,
                                 'openPrice': orders[i]['price'],
                                 'openOrderNo': orders[i]['orderNo'],  
                                    }
                            break
                        elif(self.orders[i]['side']=='SHORT'
                        and ASK <= self.orders[i]['price'] - self.symbol['margin']):
                            ordersend = {'symbol': self.symbol['symbol'],
                                 'side':'LONG',
                                 'price':BID,
                                 'vol':self.symbol['vol'],
                                 'order_status':'close',
                                 'list_del':i,
                                 'openPrice': self.orders[i]['price'],
                                 'openOrderNo': self.orders[i]['orderNo'],  
                                    }
                            break
                
                #--------------------------------open order-----------------------------------
                if(ordersend=={}):
                    #------condition long------
                    conditionLong = ASK <= self.indecator['ma'] - self.symbol['margin']
                    checkOrderLong = len(
                                        list(
                                            filter(
                                                lambda x: 
                                                    x['side']=='LONG' 
                                                    and x['price'] == (ASK < x['price']+self.symbol['margin']  
                                                                    and ASK > x['price']-self.symbol['margin'] )
                                                , self.orders
                                            )
                                        )
                                    ) > 0

                    if(conditionLong and checkOrderLong and checkEquity):
                        ordersend = {'symbol': self.symbol['symbol'],
                                     'side':'LONG',
                                     'price':ASK,
                                     'vol':self.symbol['vol'],
                                     'order_status':'open'
                                    }
               

                    #------condition Short------
                    conditionShort = BID >= self.indecator['ma'] + self.symbol['margin']
                    checkOrderShort = len(
                                        list(
                                            filter(
                                                lambda x: 
                                                    x['side']=='SHORT' 
                                                    and x['price'] == (BID < x['price']+self.symbol['margin']  
                                                                    and BID > x['price']-self.symbol['margin'] )
                                                , self.orders
                                            )
                                        )
                                    ) > 0
                    if(conditionShort and checkOrderShort and checkEquity):
                        ordersend = {'symbol': self.symbol['symbol'],
                                     'side':'SHORT',
                                     'price':BID,
                                     'vol':self.symbol['vol'],
                                     'order_status':'open'}
                    
                    
                #------sendOrder------
                if(len(ordersend)!=0):
                    res = self.placeOrder(  ordersend['symbol'],
                                            ordersend['price'],
                                            ordersend['vol'],
                                            ordersend['side'],
                                            "AUTO")
                    
                    if(res['success'] == True):
                        res=res['Data']
                        res['order_status'] = ordersend['order_status']
                    
                        #---rejectOrder---
                        if(res['reject_code'] == 1):
                            print(f"rejectOrder:{res['reject_reason']}")
                            self.alert = True
                            
                            
                        
                        #---match---  
                        elif(res['reject_code'] == 0 and res['status'] in ["M" , "MP"]):#check response'
                            #--manage list--
                            #--open order
                            if(ordersend['order_status'] == 'open'): 

                                print(f"{res['order_status']} {res['orderNo']} {res['entry']} {res['symbol']} {res['side']} {res['price']} {res['qty']}",end="\r")
                                print("")
                                self.database.save(res)
                                self.orders.append(res)
                                
                            #--close order 
                            elif(ordersend['order_status'] == 'close'):
                                res['openOrderNo'] = ordersend['openOrderNo']
                                res['openPrice'] = ordersend['openPrice']
                                #--cal profit--
                                #-close long-
                                if(res['side']=='SHORT'):
                                    res['profit'] = (res['price'] - res['openPrice'])*self.symbol['muntiply']
                                #-close short-
                                elif(res['side']=='LONG'):
                                    res['profit'] = (res['openPrice'] - res['price'])*self.symbol['muntiply']
                                    
                                print(f"{res['order_status']} {res['orderNo']} {res['entry']} {res['symbol']} {res['side']} {res['price']} {res['qty']}",end="\r")
                                print("")
                                query={'orderNo':res['orderNo']}
                                self.database.update(query,res)
                                self.orders.pop(ordersend['list_del'])
   
                            self.sendMsg(res)
                            self.alert = False
                                                 
                    #---dont match--- 
                    else:
                        print(f"order don't match")
                        self.alert = True
                            
                #--------------------------------alert-----------------------------------
                if(self.alert  == True):
                    winsound.Beep(5000, 500)
                    winsound.Beep(5000, 500)
                    winsound.Beep(5000, 500)
            

                if(self.test == True):
                    print(f"Test | System1 : {self.symbol['symbol']} ask:{ASK} ma:{round(self.indecator['ma'],3)} {tmFormat}",end="\r")
                else:
                    print(f"System1 : {self.symbol['symbol']} ask:{ASK} ma:{round(self.indecator['ma'],3)} {tmFormat}",end="\r")
            
        else:
            time.sleep(1) 
            print(f'System1 Market close  {tmFormat}',end="\r")

#--------------------------------------------------------------------------------------------------
cst =  CSTsystem()
cst.initialization()               
while(True):
    cst.main()