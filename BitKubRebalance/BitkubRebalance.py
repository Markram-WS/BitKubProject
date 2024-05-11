import datetime
from datetime import datetime as dt
import numpy as np
from BitkubTrade import Bitkub
from mongoDB import database
import time 
#-------------------------------------------------------
# API info
API_HOST = 'https://api.bitkub.com'
API_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
API_SECRET = b'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# database info
mongo = database(
    database='trading_db'
    ,collection= 'bitkubRebalance'
    ,mongodb_srv="mongodb+srv://xxxx:xxxx@cluster0.ujivx.gcp.mongodb.net/trading_db?retryWrites=true&w=majority"
    ,line_token='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    )
#-------------------------------------------------------
def initialization():  
    print("----------- Initialize -----------")
    #--------------------------variable-----------------------------
    #API
    global _bitkubAPI
    _bitkubAPI=Bitkub(API_HOST,API_KEY,API_SECRET)

    #ProductSetting
    global _symbol, _symbolSplit, _symbol_1, _symbol_2, _sym2Convert
    _symbol = 'THB_XRP'  # THB_XRP
    _symbolSplit =  _symbol.split("_")
    _symbol_1  = _symbolSplit[0]
    _symbol_2   = _symbolSplit[1]
    _sym2Convert = _symbolSplit[1]+"con"

    #Rebalance
    global _rebalance
    _rebalance = 11 # min 10 THB

    #Port
    getBalance()
    print(f'symbol: {_symbol}')
    print(f'rebalance: {_rebalance}')

    #SystemSetting
    global _system
    _system = True

    print("------------- Start -------------")
#-------------------------------------------------------
def getBalance():
    global _BalanceCon, _amt_1, _amt_2
    try:
        #-----balance-----
        _amt_1 = _bitkubAPI.balance()[_symbol_1]['available']
        _amt_2 = _bitkubAPI.balance()[_symbol_2]['available']
        _BalanceCon = True
    except:
        print(f'{_bitkubAPI.balance()}                   ',end="\r")
        _BalanceCon = False


def getAsk():
    global _AskCon, _rateAsk, _amtAsk, _volAsk, _tsAsk 
    try:
        #-----ASK-----
        Ask = _bitkubAPI.asks(_symbol)
        _tsAsk   = Ask[0][1]
        _volAsk  = Ask[0][2]
        _amtAsk  = Ask[0][4]
        _rateAsk = Ask[0][3]
        _AskCon = True
    except:
        print(f'Error:{Ask}                   ',end="\r")
        _AskCon = False


def getBid():
    global _BidCon, _rateBid, _amtBid, _volBid, _tsBid 
    try:       
        #-----BID-----
        Bid = _bitkubAPI.bids(_symbol)
        _tsBid   = Bid[0][1]
        _volBid  = Bid[0][2]
        _amtBid  = Bid[0][4]
        _rateBid = Bid[0][3]
        _BidCon = True
    except:
        print(f'Error:{Bid}                               ',end="\r")
        _BidCon = False

def msgOrder(res,side,totalAmt,balanceAmt):
    tsOrder = datetime.datetime.fromtimestamp(res['ts'])
    if(side=='buy'):
        sym = _symbol_2
    else:
        sym = _symbol_1
    print(f"{side} {_symbol} {res['amt']} {sym} at { res['rat']}  total:{round(totalAmt, 2)}|{round(balanceAmt, 2)}  {tsOrder}",end="\r")
    print('')
    mongo.lineMsg(f" {side} {_symbol} {res['amt']} {sym}\r\n at { res['rat']}  total:{round(totalAmt, 2)}|{round(balanceAmt, 2)}")
    mongo.save({
                        'position':side,
                        'symbol':sym,
                        'amt':res['amt'],
                        'rat':res['rat'],
                        'total':round(totalAmt, 2),
                        'time':tsOrder
                        })

def main(): 
    getAsk()
    if(_BalanceCon and _AskCon and _system):
        #reblanceCondition
        #-----callculate-----
        amt2Convert = _amt_2*_rateAsk
        totalAmt =_amt_1+ amt2Convert
        balanceAmt = totalAmt/2
 
        #-----Order buy Sent-----
        amt2Re = (amt2Convert-balanceAmt)/2
        if(amt2Re > _rebalance): 
            amtRe = amtRe/_rateAsk         #amtRe Convert 
            res = _bitkubAPI.placeOrder(_symbol,'buy', amt2Re, _rateAsk, 'market')
            if('error' not in res):
                msgOrder(res,'buy',totalAmt,balanceAmt)
            else:
                print(res,end="\r")
                print('')
            getBalance()    

        #-----Order sell Sent-----
        amt1Re = (_amt_1-balanceAmt)/2
        if(amt1Re > _rebalance): 
            res = _bitkubAPI.placeOrder(_symbol,'sell', amt1Re, _rateAsk, 'market')
            if('error' not in res):
                msgOrder(res,'sell',totalAmt,balanceAmt)     
            else:
                print(res,end="\r")
                print('')
            getBalance()
                
        rebalanceGauge = (max(amt2Re,amt1Re)/_rebalance)*100
        print(f'{_symbol_1}:{round(_amt_1, 2)} {_sym2Convert}:{round(amt2Convert, 2)} {_rateAsk} total:{round(totalAmt, 2)}|{round(balanceAmt, 2)}({round(rebalanceGauge)}%)  {datetime.datetime.fromtimestamp(_tsAsk)}',end="\r")
       
#-------------------------------------------------------
initialization()
while(_system):
    main()
    time.sleep(1)
