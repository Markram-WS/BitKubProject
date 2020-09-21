from pymongo import MongoClient,results 
_client=MongoClient("mongodb+srv://wasan:1234@cluster0.ujivx.gcp.mongodb.net/trading_db?retryWrites=true&w=majority")
_db=_client.get_database('trading_db')   
_db['bitkub_trade'].find({}):